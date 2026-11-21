"""Entité téléphone admin, suppression d'une sœur et migration des entrées."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.deferred_restart.admin_phone import (
    ATTR_NOTIFY_SERVICE,
    CONF_ADMIN_NOTIFY_TARGET,
    find_admin_targets,
)
from custom_components.deferred_restart.const import (
    CONF_BEFORE,
    CONF_EXCLUDE,
    CONF_PAUSE,
    DEFAULTS,
    DOMAIN,
)

from .conftest import add_sibling_target

PHONE = "notify.mobile_app_pixel_9"


def _admin_entity_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_admin_notify_target"
    )
    assert entity_id is not None
    return entity_id


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_admin_entity_follows_convention(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=2,
        data={CONF_ADMIN_NOTIFY_TARGET: PHONE},
        options=DEFAULTS,
    )
    await _setup(hass, entry)

    entity_id = _admin_entity_id(hass, entry)
    state = hass.states.get(entity_id)
    assert state.state == PHONE
    assert state.attributes[ATTR_NOTIFY_SERVICE] == PHONE
    assert er.async_get(hass).async_get(entity_id).entity_category is EntityCategory.DIAGNOSTIC
    # Une future intégration sœur nous verra
    assert find_admin_targets(hass) == [PHONE]


async def test_unset_target_is_unknown(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=2,
        data={CONF_ADMIN_NOTIFY_TARGET: None},
        options=DEFAULTS,
    )
    await _setup(hass, entry)
    state = hass.states.get(_admin_entity_id(hass, entry))
    assert state.state == "unknown"
    assert state.attributes[ATTR_NOTIFY_SERVICE] is None


async def test_sibling_removed_value_kept(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    """La valeur reprise d'une sœur est copiée : elle survit à sa suppression."""
    sibling = add_sibling_target(hass, "entity_inventory", "notify.mobile_app_sister")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADMIN_NOTIFY_TARGET: "notify.mobile_app_sister"}
    )
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    # Suppression de l'intégration sœur : son entité disparaît du registre et des états
    er.async_get(hass).async_remove(sibling)
    hass.states.async_remove(sibling)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.data[CONF_ADMIN_NOTIFY_TARGET] == "notify.mobile_app_sister"
    state = hass.states.get(_admin_entity_id(hass, entry))
    assert state.state == "notify.mobile_app_sister"
    # Lecture seule : nous n'avons rien recréé chez la sœur
    assert hass.states.get(sibling) is None


async def test_migration_from_0_2_0_keeps_options(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    """Entrée v0.2.0 (version 1.1, data vide) : migrée en 1.2 sans perte."""
    old_options = {**DEFAULTS, CONF_BEFORE: 25, CONF_PAUSE: 90, CONF_EXCLUDE: ["automation.x"]}
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, minor_version=1, data={}, options=old_options
    )
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.minor_version == 2
    assert entry.data == {CONF_ADMIN_NOTIFY_TARGET: None}
    assert dict(entry.options) == old_options
    assert hass.states.get(_admin_entity_id(hass, entry)).state == "unknown"


async def test_migration_refuses_future_version(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, version=2, minor_version=1, data={}, options=DEFAULTS)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_unload_restores_restart_service(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    original = hass.services._services["homeassistant"]["restart"].job.target
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, minor_version=2, data={CONF_ADMIN_NOTIFY_TARGET: None},
        options=DEFAULTS,
    )
    await _setup(hass, entry)
    wrapped = hass.services._services["homeassistant"]["restart"].job.target
    assert wrapped != original

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    restored = hass.services._services["homeassistant"]["restart"].job.target
    assert restored == original
