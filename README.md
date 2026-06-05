# SECHEEP Tariffs

Home Assistant custom integration for SECHEEP electricity tariff data in Chaco, Argentina.

## Status

Planned scaffold. Parser and sensors are not implemented yet.

## Goal

- Fetch SECHEEP published tariff tables.
- Parse residential electricity rates, fixed charges, subsidy variants, and kWh ranges.
- Expose Home Assistant sensors usable by the Energy dashboard and custom cost views.

## Source

Primary source:

- `https://www.secheep.gob.ar/?page_id=5601`

Fallback/cross-check source:

- `https://www.argentina.gob.ar/economia/energia/energia-electrica/estadisticas/cuadros-tarifarios-secheep`

## Planned Entities

- `sensor.secheep_current_energy_price`
- `sensor.secheep_marginal_energy_price`
- `sensor.secheep_average_energy_price`
- `sensor.secheep_fixed_charge`
- `sensor.secheep_estimated_cycle_cost`
- `sensor.secheep_tariff_valid_from`
- `binary_sensor.secheep_tariff_data_current`

