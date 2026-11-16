"""Deferred Restart : diffère les redémarrages autour des déclenchements programmés."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .guard import DeferredRestart

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

type DeferredRestartConfigEntry = ConfigEntry[DeferredRestart]


async def async_setup_entry(hass: HomeAssistant, entry: DeferredRestartConfigEntry) -> bool:
    guard = DeferredRestart(hass, entry)
    await guard.async_start()
    entry.runtime_data = guard
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DeferredRestartConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded


async def _async_reload(hass: HomeAssistant, entry: DeferredRestartConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
