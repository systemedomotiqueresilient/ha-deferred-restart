"""Fixtures communes des tests Deferred Restart."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.deferred_restart.admin_phone import ATTR_NOTIFY_SERVICE

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Autorise le chargement de custom_components/ dans chaque test."""
    return


@pytest.fixture
def restart_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Remplace le vrai homeassistant.restart par un espion (sinon HA s'arrêterait)."""
    calls: list[ServiceCall] = []

    async def _spy(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register("homeassistant", "restart", _spy)
    return calls


@pytest.fixture
def notify_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Services notify factices : un téléphone mobile_app et un service non mobile."""
    calls: list[ServiceCall] = []

    async def _spy(call: ServiceCall) -> None:
        calls.append(call)

    for name in ("mobile_app_pixel_9", "smtp"):
        hass.services.async_register("notify", name, _spy)
    return calls


def add_sibling_target(
    hass: HomeAssistant, platform: str, value: str | None, entry_id: str = "sibling"
) -> str:
    """Simule l'entité « téléphone admin » d'une intégration sœur."""
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "sensor",
        platform,
        f"{entry_id}_admin_notify_target",
        suggested_object_id=f"{platform}_{entry_id}_admin_phone",
    )
    hass.states.async_set(entity.entity_id, value or "unknown", {ATTR_NOTIFY_SERVICE: value})
    return entity.entity_id
