from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_BILLING_CYCLE_KWH,
    CONF_MANUAL_BAND_INDEX,
    CONF_SERVICE_AREA,
    CONF_SUBSIDY_PROFILE,
    COORDINATOR,
    DEFAULT_BILLING_CYCLE_KWH,
    DEFAULT_MANUAL_BAND_INDEX,
    DEFAULT_SERVICE_AREA,
    DOMAIN,
    SUBSIDY_PROFILE_UNKNOWN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS = ["sensor", "binary_sensor"]

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {
                vol.Optional(
                    CONF_SERVICE_AREA, default=DEFAULT_SERVICE_AREA
                ): cv.string,
                vol.Optional(
                    CONF_SUBSIDY_PROFILE, default=SUBSIDY_PROFILE_UNKNOWN
                ): cv.string,
                vol.Optional(
                    CONF_BILLING_CYCLE_KWH, default=DEFAULT_BILLING_CYCLE_KWH
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_MANUAL_BAND_INDEX, default=DEFAULT_MANUAL_BAND_INDEX
                ): vol.Coerce(int),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up SECHEEP Tariffs YAML import."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=config.get(DOMAIN) or {},
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SECHEEP Tariffs from a config entry."""
    from .coordinator import SecheepTariffCoordinator

    coordinator = SecheepTariffCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {COORDINATOR: coordinator}
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload SECHEEP Tariffs after options changes."""
    await hass.config_entries.async_reload(entry.entry_id)
