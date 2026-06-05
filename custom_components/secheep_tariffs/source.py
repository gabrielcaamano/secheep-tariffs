from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import urljoin

from .const import FALLBACK_SOURCE_URL, SOURCE_URL


SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


@dataclass(frozen=True)
class TariffSourceDocument:
    """One document linked from a SECHEEP tariff source index."""

    effective_date: date
    title: str
    url: str
    source_url: str
    document_type: str
    variant: str | None = None

    @property
    def is_pdf(self) -> bool:
        return self.url.lower().split("?", 1)[0].endswith(".pdf")

    @property
    def is_xlsx(self) -> bool:
        return self.url.lower().split("?", 1)[0].endswith(".xlsx")


class _TextAndLinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self._href_stack: list[str] = []
        self._link_text: list[str] = []
        self.events: list[tuple[str, str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href_stack.append(urljoin(self._base_url, _clean_href(href)))
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._href_stack:
            return
        href = self._href_stack.pop()
        title = _squash_spaces(" ".join(self._link_text))
        if title:
            self.events.append(("link", title, href))
        self._link_text = []

    def handle_data(self, data: str) -> None:
        text = _squash_spaces(data)
        if not text:
            return
        if self._href_stack:
            self._link_text.append(text)
            return
        self.events.append(("text", text, None))


def parse_secheep_source_index(
    html: str, source_url: str = SOURCE_URL
) -> list[TariffSourceDocument]:
    """Parse SECHEEP Cuadros Tarifarios HTML into dated document links."""
    parser = _TextAndLinkParser(source_url)
    parser.feed(html)

    current_date: date | None = None
    documents: list[TariffSourceDocument] = []
    for event_type, text, href in parser.events:
        parsed_date = parse_spanish_effective_date(text)
        if parsed_date is not None:
            current_date = parsed_date
            continue
        if event_type != "link" or href is None or current_date is None:
            continue
        if not _is_supported_document_url(href):
            continue
        documents.append(
            TariffSourceDocument(
                effective_date=current_date,
                title=text,
                url=href,
                source_url=source_url,
                document_type=_classify_document(text),
                variant=_classify_variant(text),
            )
        )
    return documents


def parse_argentina_source_index(
    html: str, source_url: str = FALLBACK_SOURCE_URL
) -> list[TariffSourceDocument]:
    """Parse Argentina.gob.ar fallback links into monthly XLSX documents."""
    parser = _TextAndLinkParser(source_url)
    parser.feed(html)

    documents: list[TariffSourceDocument] = []
    for event_type, text, href in parser.events:
        if event_type != "link" or href is None:
            continue
        effective_date = parse_month_year_title(text)
        if effective_date is None or not _is_supported_document_url(href):
            continue
        documents.append(
            TariffSourceDocument(
                effective_date=effective_date,
                title=text,
                url=href,
                source_url=source_url,
                document_type="xlsx",
            )
        )
    return documents


def latest_tariff_documents(
    documents: list[TariffSourceDocument],
) -> list[TariffSourceDocument]:
    """Return all tariff-table documents for the newest effective date."""
    tariff_docs = [doc for doc in documents if is_tariff_table_document(doc)]
    if not tariff_docs:
        return []
    newest = max(doc.effective_date for doc in tariff_docs)
    return [doc for doc in tariff_docs if doc.effective_date == newest]


def select_primary_tariff_document(
    documents: list[TariffSourceDocument],
) -> TariffSourceDocument | None:
    """Pick preferred current tariff table document from an index."""
    candidates = latest_tariff_documents(documents)
    if not candidates:
        return None
    preferred = [
        doc
        for doc in candidates
        if doc.variant != "without_subsidy" and doc.document_type == "annex"
    ]
    if preferred:
        return preferred[0]
    return candidates[0]


def is_tariff_table_document(document: TariffSourceDocument) -> bool:
    text = _normalize(document.title)
    if not (document.is_pdf or document.is_xlsx):
        return False
    if "solo resolucion" in text or "sin anexos" in text:
        return False
    if document.is_xlsx:
        return True
    return "anexo" in text or "cuadro tarifario" in text


def parse_spanish_effective_date(text: str) -> date | None:
    match = re.search(
        r"desde\s+el\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})",
        _normalize(text),
    )
    if not match:
        return None
    day = int(match.group(1))
    month = SPANISH_MONTHS.get(match.group(2))
    year = int(match.group(3))
    if month is None:
        return None
    return date(year, month, day)


def parse_month_year_title(text: str) -> date | None:
    match = re.search(r"(\d{2})-(\d{4})", text)
    if not match:
        return None
    return date(int(match.group(2)), int(match.group(1)), 1)


def _is_supported_document_url(url: str) -> bool:
    clean_url = url.lower().split("?", 1)[0]
    return clean_url.endswith((".pdf", ".xlsx"))


def _clean_href(href: str) -> str:
    href = unescape(href)
    if href.startswith("blank:#"):
        return href.removeprefix("blank:#")
    return href


def _classify_document(title: str) -> str:
    text = _normalize(title)
    if "anexo" in text:
        return "annex"
    if "res" in text or "resolucion" in text:
        return "resolution"
    if "xlsx" in text:
        return "xlsx"
    return "tariff"


def _classify_variant(title: str) -> str | None:
    text = _normalize(title)
    if "sin subsidio" in text or "sin sef" in text:
        return "without_subsidy"
    if "con subsidio" in text or "con sef" in text:
        return "with_subsidy"
    return None


def _normalize(text: str) -> str:
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "Á": "a",
        "É": "e",
        "Í": "i",
        "Ó": "o",
        "Ú": "u",
    }
    normalized = "".join(replacements.get(char, char) for char in text)
    return _squash_spaces(normalized).lower()


def _squash_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
