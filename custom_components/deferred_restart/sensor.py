"""Capteurs Deferred Restart."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeferredRestartConfigEntry
from .entity import DeferredRestartEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DeferredRestartConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([NextScheduledTrigger(entry.runtime_data, "next_scheduled_trigger")])


class NextScheduledTrigger(DeferredRestartEntity, SensorEntity):
    """Prochain déclenchement prévisible (sur 24 h)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        ev = self.guard.next_event
        return ev.when if ev else None

    @property
    def extra_state_attributes(self) -> dict:
        ev = self.guard.next_event
        if ev is None:
            return {}
        return {"automation": ev.entity_id, "name": ev.name, "trigger": ev.kind}
