# SECHEEP Tariffs

Home Assistant custom integration for SECHEEP electricity tariff data in Chaco, Argentina.

## Status

Early MVP. Tested on a live Home Assistant instance in Resistencia with the
unsubsidized residential profile. The integration can:

- Discover SECHEEP tariff documents from the official Cuadros Tarifarios page.
- Detect current SECHEEP scanned/image-only PDFs and keep diagnostics instead of replacing good data with bad data.
- Parse the official Argentina.gob.ar SECHEEP XLSX fallback table.
- Cache the last successful parsed tariff in Home Assistant storage.
- Expose tariff price, fixed charge, effective date, and source-status entities.
- Calculate progressive variable charges across all applicable kWh bands.

The current May 2026 SECHEEP PDF fixture is image-only, so direct primary PDF parsing needs OCR or another structured SECHEEP source. Until then, fallback XLSX data is marked as fallback/not current.

## Installation

### HACS custom repository

1. Open HACS.
2. Select the three-dot menu, then **Custom repositories**.
3. Add `https://github.com/gabrielcaamano/secheep-tariffs` as an **Integration**.
4. Install **SECHEEP Tariffs** and restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration** and select **SECHEEP Tariffs**.

### Manual

Copy `custom_components/secheep_tariffs` into the Home Assistant
`/config/custom_components` directory, then restart Home Assistant.

## Configuration

The config flow asks for:

- `service_area`, default `Resistencia`
- `subsidy_profile`
- `billing_cycle_kwh`, optional current cycle consumption used for marginal and average price
- `manual_band_index`, used when no cycle consumption exists

Choose `n1_no_subsidy` for an unsubsidized residential supply. If
`subsidy_profile` is `unknown`, price sensors stay `unknown` rather than
guessing the tariff profile.

SECHEEP variable charges are progressive. For example, consumption crossing
multiple ranges is calculated as the sum of the energy inside each range, not
as the highest reached rate multiplied by all consumed kWh.

## Energy Dashboard

Use `sensor.secheep_tariffs_current_energy_price` as the current electricity
price entity. Its `price_mode` attribute explicitly reports whether it uses a
marginal price or a manually selected band.

The integration cannot measure home consumption. A cumulative kWh meter is
still required as the Energy Dashboard grid-consumption source.

## Entities

- `sensor.secheep_tariffs_current_energy_price`
- `sensor.secheep_tariffs_marginal_energy_price`
- `sensor.secheep_tariffs_average_energy_price`
- `sensor.secheep_tariffs_fixed_charge`
- `sensor.secheep_tariffs_estimated_cycle_cost`
- `sensor.secheep_tariffs_tariff_valid_from`
- `binary_sensor.secheep_tariffs_tariff_data_current`

## Source

Primary source:

- `https://www.secheep.gob.ar/?page_id=5601`

Fallback/cross-check source:

- `https://www.argentina.gob.ar/economia/energia/energia-electrica/estadisticas/cuadros-tarifarios-secheep`

N2/N3 currently map to the public SEF table because the fallback XLSX groups
subsidized residential users as SEF.

## Known Limitations

- Current primary SECHEEP tariff PDFs are scanned images. Until direct OCR
  support exists, the integration uses the official structured fallback and
  marks it as fallback/not current.
- Tax, municipal fee, and invoice-specific adjustments are not included.
- Automatic personal subsidy eligibility lookup is intentionally unsupported.
