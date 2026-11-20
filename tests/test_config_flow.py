"""Config flow et options flow : préremplissage du téléphone admin."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.data_entry_flow import FlowResultType
import voluptuous as vol

from custom_components.deferred_restart.admin_phone import CONF_ADMIN_NOTIFY_TARGET
from custom_components.deferred_restart.const import CONF_BEFORE, DEFAULTS, DOMAIN

from .conftest import add_sibling_target

PHONE = "notify.mobile_app_pixel_9"


def _target_field(result: dict[str, Any]) -> tuple[str | None, list[str]]:
    """(valeur suggérée, liste de choix) du champ téléphone admin d'un formulaire."""
    schema: vol.Schema = result["data_schema"]
    for key, selector in schema.schema.items():
        if key == CONF_ADMIN_NOTIFY_TARGET:
            suggested = (key.description or {}).get("suggested_value")
            return suggested, list(selector.config["options"])
    raise AssertionError("champ admin_notify_target absent")


async def _start(hass: HomeAssistant) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    return result


async def test_none_found_proposes_mobile_services(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    """Aucune sœur : rien de prérempli, choix = services notify.mobile_app_*."""
    result = await _start(hass)
    assert _target_field(result) == (None, [PHONE])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADMIN_NOTIFY_TARGET: PHONE}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ADMIN_NOTIFY_TARGET: PHONE}
    # La cible n'est pas mélangée aux réglages
    assert CONF_ADMIN_NOTIFY_TARGET not in result["options"]
    assert result["options"][CONF_BEFORE] == DEFAULTS[CONF_BEFORE]


async def test_one_sibling_value_is_prefilled(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    add_sibling_target(hass, "partition_map", "notify.mobile_app_sister")
    result = await _start(hass)
    suggested, choices = _target_field(result)
    assert suggested == "notify.mobile_app_sister"
    assert choices[0] == "notify.mobile_app_sister"
    assert PHONE in choices


async def test_several_sibling_values_give_a_choice(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    add_sibling_target(hass, "partition_map", "notify.mobile_app_a", "e1")
    add_sibling_target(hass, "entity_inventory", "notify.mobile_app_b", "e2")
    add_sibling_target(hass, "sentinel_report", "notify.mobile_app_a", "e3")  # doublon
    result = await _start(hass)
    suggested, choices = _target_field(result)
    assert suggested is None
    assert choices[:2] == ["notify.mobile_app_a", "notify.mobile_app_b"]


async def test_unlisted_platform_is_ignored(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    add_sibling_target(hass, "some_other_integration", "notify.mobile_app_intruder")
    result = await _start(hass)
    suggested, choices = _target_field(result)
    assert suggested is None
    assert "notify.mobile_app_intruder" not in choices


async def test_empty_target_is_stored_as_none(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ADMIN_NOTIFY_TARGET: None}


async def test_invalid_target_is_rejected(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADMIN_NOTIFY_TARGET: "mobile_app_pixel_9"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ADMIN_NOTIFY_TARGET: "invalid_target"}


async def test_options_flow_changes_target_in_data(
    hass: HomeAssistant, restart_calls: list[ServiceCall], notify_calls: list[ServiceCall]
) -> None:
    result = await _start(hass)
    await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADMIN_NOTIFY_TARGET: PHONE}
    )
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert _target_field(result)[0] == PHONE  # valeur actuelle prioritaire

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ADMIN_NOTIFY_TARGET: "notify.smtp", CONF_BEFORE: 20}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_ADMIN_NOTIFY_TARGET] == "notify.smtp"
    assert entry.options[CONF_BEFORE] == 20
    assert CONF_ADMIN_NOTIFY_TARGET not in entry.options

    state = hass.states.get("sensor.deferred_restart_admin_phone")
    assert state is not None
    assert state.state == "notify.smtp"


async def test_options_flow_invalid_target(
    hass: HomeAssistant, restart_calls: list[ServiceCall]
) -> None:
    result = await _start(hass)
    await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ADMIN_NOTIFY_TARGET: "pas_une_cible"}
    )
    assert result["errors"] == {CONF_ADMIN_NOTIFY_TARGET: "invalid_target"}
    assert entry.data[CONF_ADMIN_NOTIFY_TARGET] is None
