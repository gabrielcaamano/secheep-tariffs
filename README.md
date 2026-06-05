# SECHEEP Tariffs

Home Assistant custom integration for SECHEEP electricity tariff data in Chaco, Argentina.

## Status

Early MVP. The integration can:

- Discover SECHEEP tariff documents from the official Cuadros Tarifarios page.
- Detect current SECHEEP scanned/image-only PDFs and keep diagnostics instead of replacing good data with bad data.
- Parse the official Argentina.gob.ar SECHEEP XLSX fallback table.
- Cache the last successful parsed tariff in Home Assistant storage.
- Expose tariff price, fixed charge, effective date, and source-status entities.

The current May 2026 SECHEEP PDF fixture is image-only, so direct primary PDF parsing needs OCR or another structured SECHEEP source. Until then, fallback XLSX data is marked as fallback/not current.

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

## Configuration

The config flow asks for:

- `service_area`, default `Resistencia`
- `subsidy_profile`
- `billing_cycle_kwh`, optional manual cycle kWh for marginal/average price
- `manual_band_index`, used when no cycle kWh exists

If `subsidy_profile` is `unknown`, price sensors stay `unknown` rather than guessing the user's tariff profile. N2/N3 currently map to the public SEF table because the fallback XLSX groups subsidized residential users as SEF.
