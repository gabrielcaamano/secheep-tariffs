from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from custom_components.secheep_tariffs.const import (
    PRICE_MODE_MANUAL_BAND,
    PRICE_MODE_MARGINAL,
    PRICE_MODE_PROFILE_NOT_CONFIGURED,
    SUBSIDY_PROFILE_N1,
    SUBSIDY_PROFILE_UNKNOWN,
)
from custom_components.secheep_tariffs.parser import parse_xlsx_tariff
from custom_components.secheep_tariffs.pricing import (
    average_variable_price,
    current_price,
    estimated_cycle_cost,
    marginal_price,
)


FIXTURES = Path(__file__).parent / "fixtures"


class SecheepPricingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tariff = parse_xlsx_tariff(
            (FIXTURES / "secheep_tariff_2026_04.xlsx").read_bytes(),
            source_url="https://www.energia.gob.ar/SECHEEP/2026_04_SECHEEP.xlsx",
            effective_date=date(2026, 4, 1),
        )

    def test_unknown_profile_has_no_price(self) -> None:
        result = current_price(self.tariff, SUBSIDY_PROFILE_UNKNOWN)

        self.assertIsNone(result.value)
        self.assertEqual(result.mode, PRICE_MODE_PROFILE_NOT_CONFIGURED)
        self.assertEqual(result.reason, "subsidy_profile_not_configured")

    def test_manual_band_price_is_explicit(self) -> None:
        result = current_price(
            self.tariff,
            SUBSIDY_PROFILE_N1,
            billing_cycle_kwh=0,
            manual_band_index=2,
        )

        self.assertEqual(result.mode, PRICE_MODE_MANUAL_BAND)
        self.assertEqual(result.band.from_kwh, 150)
        self.assertEqual(result.band.to_kwh, 300)
        self.assertAlmostEqual(result.value, 185.8636)

    def test_marginal_price_uses_kwh_edges(self) -> None:
        at_edge = marginal_price(self.tariff, SUBSIDY_PROFILE_N1, 150)
        after_edge = marginal_price(self.tariff, SUBSIDY_PROFILE_N1, 151)

        self.assertEqual(at_edge.mode, PRICE_MODE_MARGINAL)
        self.assertAlmostEqual(at_edge.value, 161.0901)
        self.assertAlmostEqual(after_edge.value, 185.8636)

    def test_average_and_estimated_cycle_cost(self) -> None:
        average = average_variable_price(self.tariff, SUBSIDY_PROFILE_N1, 200)
        estimated = estimated_cycle_cost(self.tariff, SUBSIDY_PROFILE_N1, 200)

        expected_average = (
            (50 * 153.1272) + (100 * 161.0901) + (50 * 185.8636)
        ) / 200
        self.assertAlmostEqual(average.value, expected_average)
        self.assertAlmostEqual(estimated.value, expected_average * 200 + 2277.31)


if __name__ == "__main__":
    unittest.main()
