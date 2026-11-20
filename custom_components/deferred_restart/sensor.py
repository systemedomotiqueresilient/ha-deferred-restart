"""Capteurs Deferred Restart."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeferredRestartConfigEntry
from .admin_phone import ADMIN_TARGET_SUFFIX, ATTR_NOTIFY_SERVICE, CONF_ADMIN_NOTIFY_TARGET
from .entity import DeferredRestartEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DeferredRestartConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    guard = entry.runtime_data
    async_add_entities(
        [
            NextScheduledTrigger(guard, "next_scheduled_trigger"),
            # unique_id = "<entry_id>_admin_notify_target" (convention commune admin_phone)
            AdminNotifyTarget(guard, ADMIN_TARGET_SUFFIX.removeprefix("_")),
        ]
    )


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


class AdminNotifyTarget(DeferredRestartEntity, SensorEntity):
    """Téléphone de l'administrateur : cible des notifications de l'intégration.

    Lu par les intégrations sœurs à leur installation (admin_phone.py).
    La valeur vient de entry.data ; l'entrée est rechargée quand elle change.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cellphone-message"

    @property
    def native_value(self) -> str | None:
        return self.guard.entry.data.get(CONF_ADMIN_NOTIFY_TARGET)

    @property
    def extra_state_attributes(self) -> dict:
        return {ATTR_NOTIFY_SERVICE: self.native_value}
