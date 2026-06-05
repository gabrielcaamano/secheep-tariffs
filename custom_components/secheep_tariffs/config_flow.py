from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_BILLING_CYCLE_KWH,
    CONF_MANUAL_BAND_INDEX,
    CONF_SERVICE_AREA,
    CONF_SUBSIDY_PROFILE,
    DEFAULT_BILLING_CYCLE_KWH,
    DEFAULT_MANUAL_BAND_INDEX,
    DEFAULT_SERVICE_AREA,
    DOMAIN,
    SUBSIDY_PROFILE_N1,
    SUBSIDY_PROFILE_N2,
    SUBSIDY_PROFILE_N3,
    SUBSIDY_PROFILE_SEF,
    SUBSIDY_PROFILE_UNKNOWN,
)

SUBSIDY_PROFILES = {
    SUBSIDY_PROFILE_UNKNOWN: "Unknown / configure later",
    SUBSIDY_PROFILE_N1: "N1 / no subsidy",
    SUBSIDY_PROFILE_N2: "N2 / low income (maps to public SEF table)",
    SUBSIDY_PROFILE_N3: "N3 / middle income (maps to public SEF table)",
    SUBSIDY_PROFILE_SEF: "SEF / public subsidized table",
}


class SecheepTariffsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SECHEEP Tariffs."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return SecheepTariffsOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="SECHEEP Tariffs",
                data=_with_defaults(user_input),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema({}),
            errors=errors,
        )

    async def async_step_import(
        self, user_input: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Import SECHEEP config from YAML."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="SECHEEP Tariffs",
            data=_with_defaults(user_input),
        )


class SecheepTariffsOptionsFlow(config_entries.OptionsFlow):
    """Handle SECHEEP Tariffs options."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=_with_defaults(user_input))

        existing = dict(self._config_entry.data)
        existing.update(self._config_entry.options)
        return self.async_show_form(step_id="init", data_schema=_schema(existing))


def _schema(existing: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SERVICE_AREA,
                default=existing.get(CONF_SERVICE_AREA, DEFAULT_SERVICE_AREA),
            ): str,
            vol.Required(
                CONF_SUBSIDY_PROFILE,
                default=existing.get(CONF_SUBSIDY_PROFILE, SUBSIDY_PROFILE_UNKNOWN),
            ): vol.In(SUBSIDY_PROFILES),
            vol.Required(
                CONF_BILLING_CYCLE_KWH,
                default=existing.get(CONF_BILLING_CYCLE_KWH, DEFAULT_BILLING_CYCLE_KWH),
            ): vol.Coerce(float),
            vol.Required(
                CONF_MANUAL_BAND_INDEX,
                default=existing.get(CONF_MANUAL_BAND_INDEX, DEFAULT_MANUAL_BAND_INDEX),
            ): vol.Coerce(int),
        }
    )


def _with_defaults(user_input: dict[str, Any]) -> dict[str, Any]:
    data = {
        CONF_SERVICE_AREA: DEFAULT_SERVICE_AREA,
        CONF_SUBSIDY_PROFILE: SUBSIDY_PROFILE_UNKNOWN,
        CONF_BILLING_CYCLE_KWH: DEFAULT_BILLING_CYCLE_KWH,
        CONF_MANUAL_BAND_INDEX: DEFAULT_MANUAL_BAND_INDEX,
    }
    data.update(user_input or {})
    return data
