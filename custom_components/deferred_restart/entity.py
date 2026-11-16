"""Entité de base Deferred Restart."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_UPDATE
from .guard import DeferredRestart


class DeferredRestartEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, guard: DeferredRestart, key: str) -> None:
        self.guard = guard
        self._attr_unique_id = f"{guard.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, guard.entry.entry_id)},
            name="Deferred Restart",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )
