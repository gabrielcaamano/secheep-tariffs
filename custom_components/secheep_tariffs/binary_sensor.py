from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .coordinator import SecheepTariffCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SECHEEP tariff binary sensors."""
    coordinator: SecheepTariffCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    async_add_entities([SecheepTariffDataCurrentSensor(coordinator, entry)])


class SecheepTariffDataCurrentSensor(CoordinatorEntity, BinarySensorEntity):
    """Tariff data status sensor."""

    _attr_has_entity_name = True
    _attr_name = "Tariff data current"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SecheepTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
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
        return self.coordinator.data.data_current if self.coordinator.data else False

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "source_status": data.source_status if data else "unknown",
            "source_url": data.active_source_url if data else None,
            "effective_date": data.active_effective_date if data else None,
            "primary_source_url": data.primary_source_url if data else None,
            "primary_effective_date": data.primary_effective_date if data else None,
            "error": data.error if data else None,
        }
