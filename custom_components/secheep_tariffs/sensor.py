from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_BILLING_CYCLE_KWH,
    CONF_MANUAL_BAND_INDEX,
    CONF_SUBSIDY_PROFILE,
    COORDINATOR,
    DEFAULT_BILLING_CYCLE_KWH,
    DEFAULT_MANUAL_BAND_INDEX,
    DOMAIN,
    SUBSIDY_PROFILE_UNKNOWN,
)
from .coordinator import SecheepTariffCoordinator
from .pricing import (
    PriceResult,
    average_variable_price,
    current_price,
    estimated_cycle_cost,
    marginal_price,
    select_profile,
)

ENERGY_PRICE_UNIT = "ARS/kWh"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SECHEEP tariff sensors."""
    coordinator: SecheepTariffCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    async_add_entities(
        [
            SecheepCurrentEnergyPriceSensor(coordinator, entry),
            SecheepMarginalEnergyPriceSensor(coordinator, entry),
            SecheepAverageEnergyPriceSensor(coordinator, entry),
            SecheepFixedChargeSensor(coordinator, entry),
            SecheepEstimatedCycleCostSensor(coordinator, entry),
            SecheepTariffValidFromSensor(coordinator, entry),
        ]
    )


class SecheepBaseSensor(CoordinatorEntity, SensorEntity):
    """Base SECHEEP sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SecheepTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "SECHEEP Tariffs",
            "manufacturer": "SECHEEP",
        }

    @property
    def _subsidy_profile(self) -> str:
        return self._config_value(CONF_SUBSIDY_PROFILE, SUBSIDY_PROFILE_UNKNOWN)

    @property
    def _billing_cycle_kwh(self) -> float:
        return float(self._config_value(CONF_BILLING_CYCLE_KWH, DEFAULT_BILLING_CYCLE_KWH))

    @property
    def _manual_band_index(self) -> int:
        return int(self._config_value(CONF_MANUAL_BAND_INDEX, DEFAULT_MANUAL_BAND_INDEX))

    def _config_value(self, key: str, default):
        return self._entry.options.get(key, self._entry.data.get(key, default))

    @property
    def _common_attributes(self):
        data = self.coordinator.data
        tariff = data.tariff if data else None
        return {
            "source_status": data.source_status if data else "unknown",
            "data_current": data.data_current if data else False,
            "source_url": data.active_source_url if data else None,
            "effective_date": data.active_effective_date if data else None,
            "primary_source_url": data.primary_source_url if data else None,
            "primary_effective_date": data.primary_effective_date if data else None,
            "fetched_at": data.fetched_at.isoformat() if data and data.fetched_at else None,
            "error": data.error if data else None,
            "subsidy_profile": self._subsidy_profile,
            "available_profiles": [profile.id for profile in tariff.profiles]
            if tariff
            else [],
        }

    def _price_attributes(self, result: PriceResult):
        attributes = self._common_attributes
        attributes.update(
            {
                "price_mode": result.mode,
                "reason": result.reason,
                "profile": result.profile.id if result.profile else None,
                "category": result.category.id if result.category else None,
                "band": result.band.label if result.band else None,
                "band_from_kwh": result.band.from_kwh if result.band else None,
                "band_to_kwh": result.band.to_kwh if result.band else None,
                "billing_cycle_kwh": self._billing_cycle_kwh,
                "manual_band_index": self._manual_band_index,
            }
        )
        return attributes


class SecheepCurrentEnergyPriceSensor(SecheepBaseSensor):
    """Current energy price sensor for Home Assistant Energy."""

    _attr_name = "Current energy price"
    _attr_native_unit_of_measurement = ENERGY_PRICE_UNIT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SecheepTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_energy_price"

    @property
    def _result(self) -> PriceResult:
        tariff = self.coordinator.data.tariff if self.coordinator.data else None
        return current_price(
            tariff,
            self._subsidy_profile,
            billing_cycle_kwh=self._billing_cycle_kwh,
            manual_band_index=self._manual_band_index,
        )

    @property
    def native_value(self):
        return self._result.value

    @property
    def extra_state_attributes(self):
        return self._price_attributes(self._result)


class SecheepMarginalEnergyPriceSensor(SecheepBaseSensor):
    """Next-kWh price for the configured billing-cycle kWh."""

    _attr_name = "Marginal energy price"
    _attr_native_unit_of_measurement = ENERGY_PRICE_UNIT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SecheepTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_marginal_energy_price"

    @property
    def _result(self) -> PriceResult:
        tariff = self.coordinator.data.tariff if self.coordinator.data else None
        if self._billing_cycle_kwh <= 0:
            return PriceResult(None, "marginal", reason="billing_cycle_kwh_required")
        return marginal_price(tariff, self._subsidy_profile, self._billing_cycle_kwh)

    @property
    def native_value(self):
        return self._result.value

    @property
    def extra_state_attributes(self):
        return self._price_attributes(self._result)


class SecheepAverageEnergyPriceSensor(SecheepBaseSensor):
    """Average variable energy price for configured billing-cycle kWh."""

    _attr_name = "Average energy price"
    _attr_native_unit_of_measurement = ENERGY_PRICE_UNIT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SecheepTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_average_energy_price"

    @property
    def _result(self) -> PriceResult:
        tariff = self.coordinator.data.tariff if self.coordinator.data else None
        return average_variable_price(
            tariff, self._subsidy_profile, self._billing_cycle_kwh
        )

    @property
    def native_value(self):
        return self._result.value

    @property
    def extra_state_attributes(self):
        return self._price_attributes(self._result)


class SecheepFixedChargeSensor(SecheepBaseSensor):
    """Fixed charge sensor."""

    _attr_name = "Fixed charge"
    _attr_native_unit_of_measurement = "ARS"
    _attr_device_class = SensorDeviceClass.MONETARY

    def __init__(self, coordinator: SecheepTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fixed_charge"

    @property
    def native_value(self):
        data = self.coordinator.data
        tariff = data.tariff if data else None
        profile = select_profile(tariff, self._subsidy_profile) if tariff else None
        if profile is None or not profile.categories:
            return None
        return profile.categories[0].fixed_charge_ars

    @property
    def extra_state_attributes(self):
        attributes = self._common_attributes
        attributes.update(
            {
                "billing_period": "monthly",
                "billing_days": None,
            }
        )
        return attributes


class SecheepEstimatedCycleCostSensor(SecheepBaseSensor):
    """Estimated cost for configured billing-cycle kWh."""

    _attr_name = "Estimated cycle cost"
    _attr_native_unit_of_measurement = "ARS"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SecheepTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_estimated_cycle_cost"

    @property
    def _result(self) -> PriceResult:
        tariff = self.coordinator.data.tariff if self.coordinator.data else None
        return estimated_cycle_cost(
            tariff, self._subsidy_profile, self._billing_cycle_kwh
        )

    @property
    def native_value(self):
        return self._result.value

    @property
    def extra_state_attributes(self):
        return self._price_attributes(self._result)


class SecheepTariffValidFromSensor(SecheepBaseSensor):
    """Tariff valid-from sensor."""

    _attr_name = "Tariff valid from"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SecheepTariffCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_tariff_valid_from"

    @property
    def native_value(self):
        data = self.coordinator.data
        return data.tariff.effective_date if data and data.tariff else None

    @property
    def extra_state_attributes(self):
        return self._common_attributes
