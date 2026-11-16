"""Cœur de Deferred Restart : interception et report de homeassistant.restart."""
from __future__ import annotations

from datetime import datetime, timedelta
import inspect
import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Service, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AFTER,
    CONF_ANY_RUNNING,
    CONF_BEFORE,
    CONF_EXCLUDE,
    CONF_MAX_DEFER,
    CONF_MIN_PATTERN,
    CONF_PAUSE,
    DEFAULTS,
    DOMAIN,
    HORIZON,
    NOTIFICATION_ID,
    SCAN_INTERVAL,
    SERVICE_CANCEL_PENDING,
    SERVICE_FORCE_RESTART,
    SIGNAL_UPDATE,
)
from .schedule import ScheduledEvent, async_compute_schedule

_LOGGER = logging.getLogger(__name__)

HA_DOMAIN = "homeassistant"
SERVICE_RESTART = "restart"


class DeferredRestart:
    """Diffère un redémarrage tant qu'un déclenchement prévu est proche ou en cours."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.reasons: list[str] = []
        self.next_event: ScheduledEvent | None = None
        self.pending_call: ServiceCall | None = None
        self.pending_since: datetime | None = None
        self._original: Service | None = None
        self._bypass = False
        self._active = True
        self._calendar_cache: dict = {}
        self._unsub_interval = None
        # None = protection active ; sinon date (UTC) de réactivation automatique
        self.paused_until: datetime | None = None

    # ------------------------------------------------------------------ options

    def _opt(self, key: str):
        return self.entry.options.get(key, DEFAULTS[key])

    @property
    def protection_enabled(self) -> bool:
        return self.paused_until is None or dt_util.utcnow() >= self.paused_until

    @property
    def safe(self) -> bool:
        """Un redémarrage peut passer maintenant."""
        return not self.reasons or not self.protection_enabled

    # ------------------------------------------------------------- pause / dev

    @callback
    def async_pause(self, until: datetime | None = None) -> None:
        self.paused_until = until or dt_util.utcnow() + timedelta(minutes=self._opt(CONF_PAUSE))
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    @callback
    def async_resume(self) -> None:
        self.paused_until = None
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    @property
    def deadline(self) -> datetime | None:
        max_defer = self._opt(CONF_MAX_DEFER)
        if self.pending_since is None or not max_defer:
            return None
        return self.pending_since + timedelta(minutes=max_defer)

    # --------------------------------------------------------------- lifecycle

    async def async_start(self) -> None:
        original = self.hass.services._services.get(HA_DOMAIN, {}).get(SERVICE_RESTART)  # noqa: SLF001
        if original is None:
            raise HomeAssistantError("Service homeassistant.restart introuvable")
        self._original = original

        # Remplace le service du core par notre wrapper (même schéma : safe_mode etc.)
        self.hass.services.async_register(
            HA_DOMAIN, SERVICE_RESTART, self._async_handle_restart, schema=original.schema
        )
        self.hass.services.async_register(DOMAIN, SERVICE_FORCE_RESTART, self._async_handle_force)
        self.hass.services.async_register(DOMAIN, SERVICE_CANCEL_PENDING, self._async_handle_cancel)

        self._unsub_interval = async_track_time_interval(self.hass, self._async_tick, SCAN_INTERVAL)
        await self.async_evaluate()

    async def async_stop(self) -> None:
        if self._unsub_interval:
            self._unsub_interval()
        self._active = False
        current = self.hass.services._services.get(HA_DOMAIN, {}).get(SERVICE_RESTART)  # noqa: SLF001
        if self._original is not None and current is not None:
            if current.job.target == self._async_handle_restart:
                # Nous sommes au sommet de la chaîne : on restaure le handler précédent
                # (core avec sa vérification admin, ou Spook s'il était chargé avant).
                self.hass.services.async_register(
                    HA_DOMAIN,
                    SERVICE_RESTART,
                    self._original.job.target,
                    schema=self._original.schema,
                )
            # Sinon un autre composant (ex : Spook chargé après nous) nous enveloppe :
            # on reste dans la chaîne en simple relais (_active = False) pour ne pas l'écraser.
        self.hass.services.async_remove(DOMAIN, SERVICE_FORCE_RESTART)
        self.hass.services.async_remove(DOMAIN, SERVICE_CANCEL_PENDING)
        persistent_notification.async_dismiss(self.hass, NOTIFICATION_ID)

    # --------------------------------------------------------------- évaluation

    async def async_evaluate(self) -> None:
        now = dt_util.utcnow()
        before = timedelta(minutes=self._opt(CONF_BEFORE))
        after = timedelta(minutes=self._opt(CONF_AFTER))
        excluded = set(self._opt(CONF_EXCLUDE))

        events, predictable = await async_compute_schedule(
            self.hass,
            now - after,
            now + HORIZON,
            timedelta(minutes=self._opt(CONF_MIN_PATTERN)),
            self._calendar_cache,
        )

        reasons: list[str] = []
        next_event: ScheduledEvent | None = None
        for ev in events:
            if ev.entity_id in excluded:
                continue
            if ev.when - before <= now <= ev.when + after:
                at = dt_util.as_local(ev.when).strftime("%H:%M")
                reasons.append(f"{ev.name} : déclenchement {ev.kind} prévu à {at}")
            if ev.when >= now and next_event is None:
                next_event = ev

        any_running = self._opt(CONF_ANY_RUNNING)
        for state in self.hass.states.async_all("automation"):
            if state.entity_id in excluded:
                continue
            if (state.attributes.get("current") or 0) > 0 and (
                any_running or state.entity_id in predictable
            ):
                name = state.attributes.get("friendly_name", state.entity_id)
                reasons.append(f"{name} : en cours d'exécution")
        if any_running:
            for state in self.hass.states.async_all("script"):
                if state.state == "on":
                    name = state.attributes.get("friendly_name", state.entity_id)
                    reasons.append(f"{name} (script) : en cours d'exécution")

        self.reasons = reasons
        self.next_event = next_event
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    async def _async_tick(self, _now: datetime | None = None) -> None:
        if self.paused_until is not None and self.protection_enabled:
            _LOGGER.info("Fin de pause : protection réactivée")
            self.paused_until = None
        await self.async_evaluate()
        if self.pending_call is None:
            return
        if self.safe:
            _LOGGER.info("Fenêtre libre : exécution du redémarrage différé")
            await self._async_run_pending()
        elif self.deadline and dt_util.utcnow() >= self.deadline:
            _LOGGER.warning("Délai max de report atteint, redémarrage forcé : %s", self.reasons)
            await self._async_run_pending()

    # ----------------------------------------------------------------- services

    async def _async_check_admin(self, call: ServiceCall) -> None:
        if call.context.user_id:
            user = await self.hass.auth.async_get_user(call.context.user_id)
            if user is None or not user.is_admin:
                raise Unauthorized(context=call.context)

    async def _async_call_original(self, call: ServiceCall) -> None:
        assert self._original is not None
        result = self._original.job.target(call)
        if inspect.isawaitable(result):
            await result

    async def _async_handle_restart(self, call: ServiceCall) -> None:
        # Relais transparent : instance déchargée, bypass interne, ou `force` de Spook
        if not self._active or self._bypass or call.data.get("force"):
            await self._async_call_original(call)
            return
        await self._async_check_admin(call)

        await self.async_evaluate()
        if self.safe:
            await self._async_call_original(call)
            return

        if self.pending_call is None:
            self.pending_since = dt_util.utcnow()
        self.pending_call = call  # la dernière demande gagne (ex : safe_mode)
        self._notify_pending()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

        # Demande humaine (UI ou réparation HACS) : on remonte un message visible.
        # Demande d'une automatisation : on reste silencieux pour ne pas la faire échouer.
        if self._is_human_request(call):
            raise HomeAssistantError(
                "Redémarrage différé à la fin de la fenêtre protégée : "
                + " ; ".join(self.reasons)
            )

    @callback
    def _is_human_request(self, call: ServiceCall) -> bool:
        if call.context.user_id:
            return True
        # HACS (réparation « Redémarrage requis ») appelle le service sans contexte :
        # ni utilisateur, ni parent. Une automatisation ou un script laisse sa trace :
        # contexte parent, ou contexte identique à celui de son dernier état.
        if call.context.parent_id is not None:
            return False
        ctx_id = call.context.id
        for domain in ("automation", "script"):
            if any(st.context.id == ctx_id for st in self.hass.states.async_all(domain)):
                return False
        return any(
            issue.active and issue.issue_id.startswith("restart_required")
            for issue in ir.async_get(self.hass).issues.values()
        )

    async def _async_handle_force(self, call: ServiceCall) -> None:
        await self._async_check_admin(call)
        if self.pending_call is not None:
            await self._async_run_pending()
            return
        self._bypass = True
        try:
            await self.hass.services.async_call(
                HA_DOMAIN, SERVICE_RESTART, {}, blocking=True, context=call.context
            )
        finally:
            self._bypass = False

    async def _async_handle_cancel(self, call: ServiceCall) -> None:
        await self._async_check_admin(call)
        self._clear_pending()

    # ------------------------------------------------------------------ pending

    async def _async_run_pending(self) -> None:
        call = self.pending_call
        self._clear_pending()
        if call is None:
            return
        try:
            await self._async_call_original(call)
        except HomeAssistantError as err:  # ex : configuration invalide
            persistent_notification.async_create(
                self.hass,
                f"Le redémarrage différé a échoué : {err}",
                title="Deferred Restart",
                notification_id=NOTIFICATION_ID,
            )

    @callback
    def _clear_pending(self) -> None:
        self.pending_call = None
        self.pending_since = None
        persistent_notification.async_dismiss(self.hass, NOTIFICATION_ID)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    @callback
    def _notify_pending(self) -> None:
        lines = "\n".join(f"- {r}" for r in self.reasons)
        deadline = self.deadline
        limit = (
            f"\n\nRedémarrage forcé au plus tard à {dt_util.as_local(deadline):%H:%M}."
            if deadline
            else ""
        )
        persistent_notification.async_create(
            self.hass,
            f"Un redémarrage est en attente, il s'exécutera dès que possible :\n{lines}{limit}\n\n"
            "Actions : `deferred_restart.force_restart` ou `deferred_restart.cancel_pending`.",
            title="Deferred Restart : redémarrage différé",
            notification_id=NOTIFICATION_ID,
        )
