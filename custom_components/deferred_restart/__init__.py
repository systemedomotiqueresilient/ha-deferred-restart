"""Deferred Restart : diffère les redémarrages autour des déclenchements programmés."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .admin_phone import CONF_ADMIN_NOTIFY_TARGET
from .guard import DeferredRestart

_LOGGER = logging.getLogger(__name__)

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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migre les entrées créées par une version plus ancienne, sans perte."""
    if entry.version > 1:
        return False  # entrée créée par une version plus récente : pas de retour arrière

    if entry.minor_version < 2:
        # 1.1 → 1.2 (v0.3.0) : ajout du téléphone admin dans entry.data.
        # Aucune cible n'existait avant : la valeur part à None, tous les
        # réglages (entry.options) sont conservés tels quels.
        data = {**entry.data}
        data.setdefault(CONF_ADMIN_NOTIFY_TARGET, None)
        hass.config_entries.async_update_entry(entry, data=data, minor_version=2)
        _LOGGER.info("Entrée Deferred Restart migrée en version 1.2")

    return True


async def _async_reload(hass: HomeAssistant, entry: DeferredRestartConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
