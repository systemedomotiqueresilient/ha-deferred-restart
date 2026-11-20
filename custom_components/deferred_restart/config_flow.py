"""Config flow Deferred Restart."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from .admin_phone import CONF_ADMIN_NOTIFY_TARGET, normalize_target, suggest_admin_target
from .const import (
    CONF_AFTER,
    CONF_ANY_RUNNING,
    CONF_BEFORE,
    CONF_EXCLUDE,
    CONF_MAX_DEFER,
    CONF_MIN_PATTERN,
    CONF_PAUSE,
    DEFAULTS,
    DOMAIN,
)


def _schema(hass: HomeAssistant, values: dict[str, Any], current_target: str | None) -> vol.Schema:
    """Formulaire commun au config flow et à l'options flow."""
    minutes = vol.All(vol.Coerce(int), vol.Range(min=0, max=240))
    default_target, choices = suggest_admin_target(hass, current_target)
    target_key = (
        vol.Optional(CONF_ADMIN_NOTIFY_TARGET, description={"suggested_value": default_target})
        if default_target
        else vol.Optional(CONF_ADMIN_NOTIFY_TARGET)
    )
    return vol.Schema(
        {
            target_key: SelectSelector(
                SelectSelectorConfig(
                    options=choices, custom_value=True, mode=SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required(CONF_BEFORE, default=values[CONF_BEFORE]): minutes,
            vol.Required(CONF_AFTER, default=values[CONF_AFTER]): minutes,
            vol.Required(CONF_MAX_DEFER, default=values[CONF_MAX_DEFER]): minutes,
            vol.Required(CONF_MIN_PATTERN, default=values[CONF_MIN_PATTERN]): minutes,
            vol.Required(CONF_ANY_RUNNING, default=values[CONF_ANY_RUNNING]): bool,
            vol.Required(CONF_PAUSE, default=values[CONF_PAUSE]): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=1440)
            ),
            vol.Optional(CONF_EXCLUDE, default=values[CONF_EXCLUDE]): EntitySelector(
                EntitySelectorConfig(domain="automation", multiple=True)
            ),
        }
    )


def _split_target(user_input: dict[str, Any]) -> tuple[str | None, dict[str, Any], bool]:
    """Sépare la cible (entry.data) des réglages (entry.options).

    Renvoie (cible normalisée ou None, réglages, saisie valide).
    Un champ vide signifie « pas de cible » ; une saisie qui n'est pas
    du type notify.xxx est refusée.
    """
    options = dict(user_input)
    raw = options.pop(CONF_ADMIN_NOTIFY_TARGET, None)
    target = normalize_target(raw)
    valid = target is not None or not (isinstance(raw, str) and raw.strip())
    return target, options, valid


class DeferredRestartConfigFlow(ConfigFlow, domain=DOMAIN):
    """Installation de Deferred Restart."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            target, options, valid = _split_target(user_input)
            if valid:
                return self.async_create_entry(
                    title="Deferred Restart",
                    data={CONF_ADMIN_NOTIFY_TARGET: target},
                    options=options,
                )
            errors[CONF_ADMIN_NOTIFY_TARGET] = "invalid_target"
        return self.async_show_form(
            step_id="user", data_schema=_schema(self.hass, DEFAULTS, None), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return DeferredRestartOptionsFlow()


class DeferredRestartOptionsFlow(OptionsFlow):
    """Réglages et téléphone admin modifiables après installation."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = self.config_entry.data.get(CONF_ADMIN_NOTIFY_TARGET)
        if user_input is not None:
            target, options, valid = _split_target(user_input)
            if valid:
                if target != current:
                    # La cible vit dans entry.data (spec commune v0.2).
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={**self.config_entry.data, CONF_ADMIN_NOTIFY_TARGET: target},
                    )
                return self.async_create_entry(data=options)
            errors[CONF_ADMIN_NOTIFY_TARGET] = "invalid_target"
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, {**DEFAULTS, **self.config_entry.options}, current),
            errors=errors,
        )
