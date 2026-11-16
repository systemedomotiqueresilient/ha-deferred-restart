"""Calcul des prochains déclenchements prévisibles des automatisations.

Seuls les triggers dont l'heure est connue à l'avance sont pris en compte :
time (heure fixe, input_datetime, sensor timestamp), time_pattern, sun, calendar.
Les triggers d'état, d'événement, MQTT, template... sont imprévisibles et ignorés.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant, valid_entity_id
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.sun import get_astral_event_next
from homeassistant.util import dt as dt_util

from .const import CALENDAR_CACHE_TTL

_LOGGER = logging.getLogger(__name__)

PREDICTABLE_TRIGGERS = {"time", "time_pattern", "sun", "calendar"}


@dataclass(frozen=True)
class ScheduledEvent:
    """Un déclenchement prévu."""

    when: datetime  # UTC
    entity_id: str
    name: str
    kind: str


# --------------------------------------------------------------------------- utils


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _offset(raw: Any) -> timedelta:
    if raw in (None, ""):
        return timedelta()
    try:
        return cv.time_period(raw)
    except Exception:  # noqa: BLE001 - offset templaté ou invalide
        return timedelta()


def _tz():
    return dt_util.get_default_time_zone()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=_tz())


def _next_time_of_day(
    t: time, start: datetime, offset: timedelta = timedelta()
) -> datetime | None:
    """Prochaine occurrence (UTC) d'une heure locale, >= start."""
    local_start = dt_util.as_local(start)
    for days in (-1, 0, 1, 2):
        cand = datetime.combine(local_start.date() + timedelta(days=days), t, tzinfo=_tz())
        cand += offset
        if cand >= local_start:
            return dt_util.as_utc(cand)
    return None


# ------------------------------------------------------------------------ triggers


def _time_from_entity(
    hass: HomeAssistant, entity_id: str, start: datetime, offset: timedelta
) -> datetime | None:
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", ""):
        return None

    if entity_id.startswith("input_datetime."):
        has_date = state.attributes.get("has_date")
        has_time = state.attributes.get("has_time")
        if has_date and has_time:
            parsed = dt_util.parse_datetime(state.state)
            return dt_util.as_utc(_aware(parsed) + offset) if parsed else None
        if has_time:
            t = dt_util.parse_time(state.state)
            return _next_time_of_day(t, start, offset) if t else None
        if has_date:  # date seule : HA déclenche à minuit
            d: date | None = dt_util.parse_date(state.state)
            if d is None:
                return None
            return dt_util.as_utc(datetime.combine(d, time(0), tzinfo=_tz()) + offset)
        return None

    # sensor avec device_class timestamp
    parsed = dt_util.parse_datetime(state.state)
    return dt_util.as_utc(_aware(parsed) + offset) if parsed else None


def _time_trigger(hass: HomeAssistant, trig: dict, start: datetime) -> list[datetime]:
    out: list[datetime] = []
    for at in _as_list(trig.get("at")):
        offset = timedelta()
        if isinstance(at, dict):
            offset = _offset(at.get("offset"))
            at = at.get("entity_id")
        if not isinstance(at, str):
            continue
        if valid_entity_id(at):
            when = _time_from_entity(hass, at, start, offset)
        else:
            t = dt_util.parse_time(at)
            when = _next_time_of_day(t, start) if t else None
        if when is not None and when >= start:
            out.append(when)
    return out


def _matcher(value: Any) -> Callable[[int], bool]:
    s = str(value).strip()
    if s == "*":
        return lambda _x: True
    if s.startswith("/"):
        n = int(s[1:])
        return lambda x: x % n == 0
    n = int(s)
    return lambda x: x == n


def _pattern_trigger(
    trig: dict, start: datetime, end: datetime, min_interval: timedelta
) -> list[datetime]:
    hours, minutes, seconds = trig.get("hours"), trig.get("minutes"), trig.get("seconds")
    # Mêmes valeurs par défaut que le trigger time_pattern de HA
    if minutes is None and hours is not None:
        minutes = 0
    if seconds is None and minutes is not None:
        seconds = 0
    hours = "*" if hours is None else hours
    minutes = "*" if minutes is None else minutes
    sec = "*" if seconds is None else str(seconds).strip()
    if not sec.isdigit():
        return []  # plusieurs fois par minute : non pertinent
    try:
        match_h, match_m = _matcher(hours), _matcher(minutes)
    except (ValueError, ZeroDivisionError):
        return []

    cur = dt_util.as_local(start).replace(second=0, microsecond=0)
    stop = dt_util.as_local(end)
    hits: list[datetime] = []
    while cur <= stop and len(hits) < 2:
        if match_h(cur.hour) and match_m(cur.minute):
            hits.append(dt_util.as_utc(cur.replace(second=int(sec))))
        cur += timedelta(minutes=1)

    if len(hits) == 2 and hits[1] - hits[0] < min_interval:
        return []  # trop fréquent : bloquerait en permanence
    return hits


def _sun_trigger(hass: HomeAssistant, trig: dict, start: datetime) -> list[datetime]:
    event = trig.get("event")
    if event not in ("sunrise", "sunset"):
        return []
    try:
        return [get_astral_event_next(hass, event, start, _offset(trig.get("offset")))]
    except Exception:  # noqa: BLE001 - soleil qui ne se lève pas, etc.
        return []


async def _calendar_trigger(
    hass: HomeAssistant, trig: dict, start: datetime, end: datetime, cache: dict
) -> list[datetime]:
    entity_id = trig.get("entity_id")
    if not isinstance(entity_id, str):
        return []
    which = trig.get("event", "start")
    offset = _offset(trig.get("offset"))

    now = dt_util.utcnow()
    cached = cache.get(entity_id)
    if cached is None or now - cached[0] > CALENDAR_CACHE_TTL:
        component = hass.data.get("calendar")
        entity = component.get_entity(entity_id) if component else None
        if entity is None:
            return []
        try:
            events = await entity.async_get_events(
                hass, start - timedelta(hours=1), end + timedelta(hours=1)
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Calendrier %s illisible : %s", entity_id, err)
            events = []
        cached = (now, events)
        cache[entity_id] = cached

    out: list[datetime] = []
    for ev in cached[1]:
        base = ev.start_datetime_local if which == "start" else ev.end_datetime_local
        when = dt_util.as_utc(base + offset)
        if start <= when <= end:
            out.append(when)
    return out


# --------------------------------------------------------------------------- main


async def async_compute_schedule(
    hass: HomeAssistant,
    start: datetime,
    end: datetime,
    min_pattern_interval: timedelta,
    calendar_cache: dict,
) -> tuple[list[ScheduledEvent], set[str]]:
    """Retourne (déclenchements prévus dans [start, end], automatisations prévisibles)."""
    component = hass.data.get("automation")
    if component is None:
        return [], set()

    events: list[ScheduledEvent] = []
    predictable: set[str] = set()

    for entity in list(component.entities):
        entity_id = entity.entity_id
        state = hass.states.get(entity_id)
        if state is None or state.state != "on":
            continue
        name = state.attributes.get("friendly_name", entity_id)
        cfg = getattr(entity, "raw_config", None) or {}

        for trig in _as_list(cfg.get("triggers", cfg.get("trigger"))):
            if not isinstance(trig, dict) or trig.get("enabled") is False:
                continue
            kind = trig.get("trigger", trig.get("platform"))
            if kind not in PREDICTABLE_TRIGGERS:
                continue
            predictable.add(entity_id)

            try:
                if kind == "time":
                    whens = _time_trigger(hass, trig, start)
                elif kind == "time_pattern":
                    whens = _pattern_trigger(trig, start, end, min_pattern_interval)
                elif kind == "sun":
                    whens = _sun_trigger(hass, trig, start)
                else:
                    whens = await _calendar_trigger(hass, trig, start, end, calendar_cache)
            except Exception:  # noqa: BLE001 - un trigger exotique ne doit rien casser
                _LOGGER.exception("Trigger non analysable dans %s", entity_id)
                continue

            events.extend(
                ScheduledEvent(w, entity_id, name, kind) for w in whens if w <= end
            )

    events.sort(key=lambda e: e.when)
    return events, predictable
