from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_SERVICE_AREA,
    CONF_SUBSIDY_PROFILE,
    DEFAULT_SERVICE_AREA,
    DOMAIN,
)

SUBSIDY_PROFILES = {
    "unknown": "Unknown / configure later",
    "n1_no_subsidy": "N1 / no subsidy",
    "n2_low_income": "N2 / low income",
    "n3_middle_income": "N3 / middle income",
}


class SecheepTariffsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SECHEEP Tariffs."""

    VERSION = 1

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
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SERVICE_AREA, default=DEFAULT_SERVICE_AREA
                ): str,
                vol.Required(
                    CONF_SUBSIDY_PROFILE, default="unknown"
                ): vol.In(SUBSIDY_PROFILES),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

