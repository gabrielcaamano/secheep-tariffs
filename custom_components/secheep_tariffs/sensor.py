from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SOURCE_URL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SECHEEP tariff sensors."""
    async_add_entities(
        [
            SecheepCurrentEnergyPriceSensor(entry),
            SecheepFixedChargeSensor(entry),
            SecheepTariffValidFromSensor(entry),
        ]
    )


class SecheepBaseSensor(SensorEntity):
    """Base SECHEEP sensor."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "SECHEEP Tariffs",
            "manufacturer": "SECHEEP",
        }


class SecheepCurrentEnergyPriceSensor(SecheepBaseSensor):
    """Placeholder current energy price sensor."""

    _attr_name = "Current energy price"
    _attr_native_unit_of_measurement = "ARS/kWh"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_current_energy_price"

    @property
    def native_value(self):
        return None

    @property
    def extra_state_attributes(self):
        return {
            "source_url": SOURCE_URL,
            "price_mode": "not_implemented",
        }


class SecheepFixedChargeSensor(SecheepBaseSensor):
    """Placeholder fixed charge sensor."""

    _attr_name = "Fixed charge"
    _attr_native_unit_of_measurement = "ARS"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_fixed_charge"

    @property
    def native_value(self):
        return None

    @property
    def extra_state_attributes(self):
        return {
            "billing_period": "unknown",
            "source_url": SOURCE_URL,
        }


class SecheepTariffValidFromSensor(SecheepBaseSensor):
    """Placeholder tariff valid-from sensor."""

    _attr_name = "Tariff valid from"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_tariff_valid_from"

    @property
    def native_value(self):
        return None

    @property
    def extra_state_attributes(self):
        return {"source_url": SOURCE_URL}

