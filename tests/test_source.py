from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from custom_components.secheep_tariffs.source import (
    latest_tariff_documents,
    parse_secheep_source_index,
    select_primary_tariff_document,
)


FIXTURES = Path(__file__).parent / "fixtures"


class SecheepSourceIndexTest(unittest.TestCase):
    def test_selects_latest_tariff_annex_not_resolution_only_date(self) -> None:
        html = (FIXTURES / "secheep_source_index.html").read_text()

        documents = parse_secheep_source_index(html)
        latest = latest_tariff_documents(documents)
        primary = select_primary_tariff_document(documents)

        self.assertGreaterEqual(len(documents), 40)
        self.assertEqual({document.effective_date for document in latest}, {date(2026, 5, 9)})
        self.assertIn("Anexo I - Cuadro Tarifario mayo 2026", [doc.title for doc in latest])
        self.assertIn(
            "Anexo II - Cuadro Tarifario Sin Subsidio mayo 2026",
            [doc.title for doc in latest],
        )
        self.assertIsNotNone(primary)
        self.assertEqual(primary.title, "Anexo I - Cuadro Tarifario mayo 2026")
        self.assertEqual(primary.document_type, "annex")


if __name__ == "__main__":
    unittest.main()
