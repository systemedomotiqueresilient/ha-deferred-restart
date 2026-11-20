"""Report du redémarrage et notifications vers le téléphone admin."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.deferred_restart.admin_phone import CONF_ADMIN_NOTIFY_TARGET
from custom_components.deferred_restart.const import DEFAULTS, DOMAIN

PHONE = "notify.mobile_app_pixel_9"


async def _scheduled_automation(hass: HomeAssistant, minutes_ahead: int = 8) -> None:
    """Automatisation à trigger time dans quelques minutes : fenêtre protégée."""
    at = (dt_util.now() + timedelta(minutes=minutes_ahead)).strftime("%H:%M:00")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "id": "volets",
                    "alias": "Volets matin",
                    "triggers": [{"trigger": "time", "at": at}],
                    "actions": [],
                }
            ]
        },
    )
    await hass.async_block_till_done()


async def _setup(hass: HomeAssistant, target: str | None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=2,
        data={CONF_ADMIN_NOTIFY_TARGET: target},
        options=DEFAULTS,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_restart_allowed_when_window_clear(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    await _setup(hass, PHONE)
    await hass.services.async_call("homeassistant", "restart", {}, blocking=True)
    assert len(restart_calls) == 1
    assert notify_calls == []


async def test_deferral_notifies_admin_phone_once(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    await _scheduled_automation(hass)
    entry = await _setup(hass, PHONE)

    # Demande d'automatisation (sans utilisateur) : report silencieux
    await hass.services.async_call("homeassistant", "restart", {}, blocking=True)
    await hass.services.async_call("homeassistant", "restart", {}, blocking=True)
    await hass.async_block_till_done()

    assert restart_calls == []
    assert entry.runtime_data.pending_call is not None
    assert len(notify_calls) == 1  # une seule notification par report
    call = notify_calls[0]
    assert call.service == "mobile_app_pixel_9"
    assert call.data["title"] == "Deferred Restart"
    assert "Volets matin" in call.data["message"]
    assert hass.states.get("binary_sensor.deferred_restart_pending").state == "on"


async def test_deferral_without_target_sends_nothing(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    await _scheduled_automation(hass)
    entry = await _setup(hass, None)
    await hass.services.async_call("homeassistant", "restart", {}, blocking=True)
    await hass.async_block_till_done()
    assert entry.runtime_data.pending_call is not None
    assert notify_calls == []


async def test_deadline_forces_restart_after_notifying(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    await _scheduled_automation(hass)
    entry = await _setup(hass, PHONE)
    guard = entry.runtime_data
    await hass.services.async_call("homeassistant", "restart", {}, blocking=True)
    await hass.async_block_till_done()
    notify_calls.clear()

    guard.pending_since = dt_util.utcnow() - timedelta(minutes=DEFAULTS["max_defer_minutes"] + 1)
    await guard._async_tick()
    await hass.async_block_till_done()

    assert len(restart_calls) == 1
    assert len(notify_calls) == 1
    assert "forcing restart" in notify_calls[0].data["message"]
    assert guard.pending_call is None


async def test_french_messages(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    hass.config.language = "fr"
    await _scheduled_automation(hass)
    await _setup(hass, PHONE)
    await hass.services.async_call("homeassistant", "restart", {}, blocking=True)
    await hass.async_block_till_done()
    assert notify_calls[0].data["message"].startswith("Redémarrage différé")


async def test_pause_releases_pending_restart(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    await _scheduled_automation(hass)
    entry = await _setup(hass, PHONE)
    await hass.services.async_call("homeassistant", "restart", {}, blocking=True)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.deferred_restart_protection"}, blocking=True
    )
    await entry.runtime_data._async_tick()
    await hass.async_block_till_done()
    assert len(restart_calls) == 1


async def test_cancel_pending(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    await _scheduled_automation(hass)
    entry = await _setup(hass, PHONE)
    await hass.services.async_call("homeassistant", "restart", {}, blocking=True)
    await hass.services.async_call(DOMAIN, "cancel_pending", {}, blocking=True)
    assert entry.runtime_data.pending_call is None
    assert restart_calls == []
