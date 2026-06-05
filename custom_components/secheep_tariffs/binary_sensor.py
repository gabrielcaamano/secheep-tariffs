from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SECHEEP tariff binary sensors."""
    async_add_entities([SecheepTariffDataCurrentSensor(entry)])


class SecheepTariffDataCurrentSensor(BinarySensorEntity):
    """Placeholder tariff data status sensor."""

    _attr_has_entity_name = True
    _attr_name = "Tariff data current"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_tariff_data_current"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "SECHEEP Tariffs",
            "manufacturer": "SECHEEP",
        }

    @property
    def is_on(self):
        return False

    @property
    def extra_state_attributes(self):
        return {"reason": "parser_not_implemented"}

