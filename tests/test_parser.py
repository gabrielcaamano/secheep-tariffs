from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from custom_components.secheep_tariffs.parser import (
    ScannedPdfError,
    looks_image_only_pdf,
    parse_pdf_tariff,
    parse_pdf_text_tariff,
    parse_xlsx_tariff,
)


FIXTURES = Path(__file__).parent / "fixtures"

PDF_TEXT_SAMPLE = """
RESIDENCIAL SIN SEF 111-114
Cargo Fijo $/MES 2.287,94 0,00 2.287,94
Cargo Variable 1ros. 50 KWh-mes $/KWh 20,0965 156,9462 177,0427
Cargo Variable stes. 100 KWh-mes $/KWh 32,2667 156,9462 189,2129
Cargo Variable stes. 150 KWh-mes $/KWh 70,1296 156,9462 227,0758
Cargo Variable exc. 300 KWh-mes $/KWh 89,0610 156,9462 246,0072
RESIDENCIAL CON SEF 111-114
Cargo Fijo $/MES 2.287,94 0,00 2.287,94
Cargo Variable 1ros. 50 KWh-mes $/KWh 20,0965 71,7901 91,8866
Cargo Variable stes. 100 KWh-mes $/KWh 32,2667 71,7901 104,0568
Cargo Variable stes. 150 KWh-mes $/KWh 70,1296 71,7901 141,9197
Cargo Variable exc. 300 KWh-mes $/KWh 89,0610 156,9462 246,0072
"""


class SecheepParserTest(unittest.TestCase):
    def test_current_pdf_fixture_is_scanned_image_only(self) -> None:
        content = (FIXTURES / "secheep_tariff_may_2026.pdf").read_bytes()

        self.assertTrue(looks_image_only_pdf(content))
        with self.assertRaises(ScannedPdfError):
            parse_pdf_tariff(
                content,
                source_url="https://www.secheep.gob.ar/wp-content/uploads/2026/05/Anexo-I-Cuadro-Tarifario-Mayo-2026.pdf",
                effective_date=date(2026, 5, 9),
            )

    def test_parse_residential_rows_from_pdf_text(self) -> None:
        tariff = parse_pdf_text_tariff(
            PDF_TEXT_SAMPLE,
            source_url="https://www.secheep.gob.ar/example.pdf",
            effective_date=date(2026, 5, 9),
        )

        self.assertEqual(tariff.schema_version, 1)
        self.assertEqual(tariff.effective_date, date(2026, 5, 9))
        self.assertEqual([profile.id for profile in tariff.profiles], [
            "residential_n1_no_subsidy",
            "residential_sef",
        ])
        no_subsidy = tariff.profiles[0].categories[0]
        sef = tariff.profiles[1].categories[0]
        self.assertAlmostEqual(no_subsidy.fixed_charge_ars, 2287.94)
        self.assertEqual([(band.from_kwh, band.to_kwh) for band in no_subsidy.bands], [
            (0, 50),
            (50, 150),
            (150, 300),
            (300, None),
        ])
        self.assertAlmostEqual(no_subsidy.bands[0].price_ars_per_kwh, 177.0427)
        self.assertAlmostEqual(no_subsidy.bands[0].components["abastecimiento"], 156.9462)
        self.assertAlmostEqual(sef.bands[0].price_ars_per_kwh, 91.8866)
        self.assertAlmostEqual(sef.bands[3].price_ars_per_kwh, 246.0072)

    def test_parse_official_xlsx_fallback_residential_rows(self) -> None:
        content = (FIXTURES / "secheep_tariff_2026_04.xlsx").read_bytes()

        tariff = parse_xlsx_tariff(
            content,
            source_url="https://www.energia.gob.ar/SECHEEP/2026_04_SECHEEP.xlsx",
            effective_date=date(2026, 4, 1),
        )

        self.assertEqual(tariff.source_url, "https://www.energia.gob.ar/SECHEEP/2026_04_SECHEEP.xlsx")
        self.assertEqual([profile.id for profile in tariff.profiles], [
            "residential_n1_no_subsidy",
            "residential_sef",
        ])
        no_subsidy = tariff.profiles[0].categories[0]
        sef = tariff.profiles[1].categories[0]
        self.assertAlmostEqual(no_subsidy.fixed_charge_ars, 2277.31)
        self.assertAlmostEqual(no_subsidy.bands[0].price_ars_per_kwh, 153.1272)
        self.assertEqual(no_subsidy.bands[-1].to_kwh, None)
        self.assertAlmostEqual(no_subsidy.bands[-1].price_ars_per_kwh, 198.2504)
        self.assertAlmostEqual(sef.bands[0].price_ars_per_kwh, 66.9682)
        self.assertAlmostEqual(sef.bands[2].price_ars_per_kwh, 185.8636)


if __name__ == "__main__":
    unittest.main()
