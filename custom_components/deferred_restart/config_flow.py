"""Config flow Deferred Restart."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

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


def _schema(values: dict[str, Any]) -> vol.Schema:
    minutes = vol.All(vol.Coerce(int), vol.Range(min=0, max=240))
    return vol.Schema(
        {
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


class DeferredRestartConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="Deferred Restart", data={}, options=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema(DEFAULTS))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return DeferredRestartOptionsFlow()


class DeferredRestartOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=_schema({**DEFAULTS, **self.config_entry.options})
        )
