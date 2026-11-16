"""Capteurs binaires Deferred Restart."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeferredRestartConfigEntry
from .entity import DeferredRestartEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DeferredRestartConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    guard = entry.runtime_data
    async_add_entities([RestartSafe(guard, "safe_now"), RestartPending(guard, "pending")])


class RestartSafe(DeferredRestartEntity, BinarySensorEntity):
    """on = un redémarrage maintenant ne gênerait aucun déclenchement prévu."""

    @property
    def is_on(self) -> bool:
        return self.guard.safe

    @property
    def extra_state_attributes(self) -> dict:
        return {"reasons": self.guard.reasons}


class RestartPending(DeferredRestartEntity, BinarySensorEntity):
    """on = un redémarrage est en attente."""

    @property
    def is_on(self) -> bool:
        return self.guard.pending_call is not None

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "pending_since": self.guard.pending_since,
            "deadline": self.guard.deadline,
        }
