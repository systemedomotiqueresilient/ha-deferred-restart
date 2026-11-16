"""Interrupteur de protection Deferred Restart (mode dev)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import DeferredRestartConfigEntry
from .entity import DeferredRestartEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DeferredRestartConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([ProtectionSwitch(entry.runtime_data, "protection")])


class ProtectionSwitch(DeferredRestartEntity, SwitchEntity, RestoreEntity):
    """off = protection en pause, réactivation automatique à `resume_at`.

    L'état est restauré après redémarrage : une pause survit aux redémarrages
    successifs d'une session de développement.
    """

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state != STATE_OFF:
            return
        resume_at = dt_util.parse_datetime(str(last.attributes.get("resume_at", "")))
        if resume_at and resume_at > dt_util.utcnow():
            self.guard.async_pause(dt_util.as_utc(resume_at))

    @property
    def is_on(self) -> bool:
        return self.guard.protection_enabled

    @property
    def extra_state_attributes(self) -> dict:
        if self.guard.protection_enabled:
            return {}
        return {"resume_at": self.guard.paused_until.isoformat()}

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.guard.async_resume()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.guard.async_pause()
