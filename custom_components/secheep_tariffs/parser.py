from __future__ import annotations

from datetime import date
from io import BytesIO
import re
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from .const import DEFAULT_SERVICE_AREA
from .models import (
    BillingPeriod,
    NormalizedTariff,
    TariffBand,
    TariffCategory,
    TariffProfile,
)


class TariffParseError(ValueError):
    """Base parser error."""


class PdfParserUnavailableError(TariffParseError):
    """Raised when a text PDF needs an optional parser dependency."""


class ScannedPdfError(TariffParseError):
    """Raised when a PDF is image-only and needs OCR."""


def parse_pdf_tariff(
    content: bytes,
    *,
    source_url: str,
    effective_date: date,
    resolution: str | None = None,
    service_area: str = DEFAULT_SERVICE_AREA,
) -> NormalizedTariff:
    """Parse a SECHEEP PDF that has extractable text."""
    text = extract_pdf_text(content)
    if not text.strip():
        if looks_image_only_pdf(content):
            raise ScannedPdfError("SECHEEP PDF appears to be image-only; OCR required")
        raise PdfParserUnavailableError(
            "No extractable PDF text found and no OCR parser is configured"
        )
    return parse_pdf_text_tariff(
        text,
        source_url=source_url,
        effective_date=effective_date,
        resolution=resolution,
        service_area=service_area,
    )


def extract_pdf_text(content: bytes) -> str:
    """Extract text with pypdf when available."""
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return ""

    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def looks_image_only_pdf(content: bytes) -> bool:
    """Detect scanned PDFs generated as image XObjects with no fonts."""
    image_count = len(re.findall(rb"/Subtype\s*/Image", content))
    font_count = content.count(b"/Font")
    return image_count > 0 and font_count == 0


def parse_pdf_text_tariff(
    text: str,
    *,
    source_url: str,
    effective_date: date,
    resolution: str | None = None,
    service_area: str = DEFAULT_SERVICE_AREA,
) -> NormalizedTariff:
    """Parse SECHEEP residential rows from extracted/OCR text."""
    lines = [_squash_spaces(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    profiles: list[TariffProfile] = []
    for profile_id, name, subsidy, header in (
        (
            "residential_n1_no_subsidy",
            "Residential without SEF",
            "n1_no_subsidy",
            "RESIDENCIAL SIN SEF 111-114",
        ),
        (
            "residential_sef",
            "Residential with SEF",
            "sef",
            "RESIDENCIAL CON SEF 111-114",
        ),
    ):
        block = _find_text_block(lines, header)
        if not block:
            continue
        category = _parse_text_category(block, "residential_111_114", "111-114")
        profiles.append(
            TariffProfile(
                id=profile_id,
                name=name,
                subsidy=subsidy,
                categories=[category],
            )
        )

    if not profiles:
        raise TariffParseError("No residential SECHEEP tariff rows found")

    return NormalizedTariff(
        provider="SECHEEP",
        service_area=service_area,
        effective_date=effective_date,
        source_url=source_url,
        resolution=resolution,
        currency="ARS",
        billing_period=BillingPeriod(),
        profiles=profiles,
    )


def parse_xlsx_tariff(
    content: bytes,
    *,
    source_url: str,
    effective_date: date,
    resolution: str | None = None,
    service_area: str = DEFAULT_SERVICE_AREA,
) -> NormalizedTariff:
    """Parse official energia.gob.ar SECHEEP XLSX residential rows."""
    rows = list(_xlsx_rows(content))
    groups = _residential_familiar_groups(rows)
    profiles: list[TariffProfile] = []

    for group in groups:
        text = _normalize(" ".join(str(cell) for row in group for cell in row))
        if "sin subsidios energeticos focalizados" in text:
            profile_id = "residential_n1_no_subsidy"
            name = "Residential without SEF"
            subsidy = "n1_no_subsidy"
        elif "con subsidios energeticos focalizados" in text or "dto pen 943" in text:
            profile_id = "residential_sef"
            name = "Residential with SEF"
            subsidy = "sef"
        else:
            continue
        category = _parse_xlsx_category(group, "residential_0111_0114", "0111-0114")
        profiles.append(
            TariffProfile(
                id=profile_id,
                name=name,
                subsidy=subsidy,
                categories=[category],
            )
        )

    if not profiles:
        raise TariffParseError("No residential SECHEEP XLSX tariff rows found")

    return NormalizedTariff(
        provider="SECHEEP",
        service_area=service_area,
        effective_date=effective_date,
        source_url=source_url,
        resolution=resolution,
        currency="ARS",
        billing_period=BillingPeriod(),
        profiles=profiles,
    )


def _find_text_block(lines: list[str], header: str) -> list[str]:
    normalized_header = _normalize(header)
    start: int | None = None
    for index, line in enumerate(lines):
        if normalized_header in _normalize(line):
            start = index
            break
    if start is None:
        return []

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = _normalize(lines[index])
        if line.startswith("residencial ") and "111-114" in line:
            end = index
            break
    return lines[start:end]


def _parse_text_category(block: list[str], category_id: str, label: str) -> TariffCategory:
    fixed_charge: float | None = None
    bands: list[TariffBand] = []
    previous_to = 0.0

    for line in block:
        numbers = _numbers_from_text(line)
        normalized = _normalize(line)
        if "cargo fijo" in normalized and numbers:
            fixed_charge = numbers[-1]
            continue
        if "$/kwh" not in normalized and "$/kw h" not in normalized:
            continue
        if not numbers:
            continue
        label_text = _clean_band_label(re.split(r"\$/kwh|\$/kw h", line, flags=re.I)[0])
        from_kwh, to_kwh = _band_bounds(label_text, previous_to)
        if to_kwh is not None:
            previous_to = to_kwh
        components = {}
        if len(numbers) >= 3:
            components = {
                "vad": numbers[-3],
                "abastecimiento": numbers[-2],
            }
        bands.append(
            TariffBand(
                label=label_text,
                from_kwh=from_kwh,
                to_kwh=to_kwh,
                price_ars_per_kwh=numbers[-1],
                components=components,
            )
        )

    if fixed_charge is None or not bands:
        raise TariffParseError(f"Incomplete residential category {label}")
    return TariffCategory(
        id=category_id,
        label=label,
        min_kwh=0,
        max_kwh=None,
        fixed_charge_ars=fixed_charge,
        bands=bands,
    )


def _parse_xlsx_category(
    rows: list[list[object]], category_id: str, label: str
) -> TariffCategory:
    fixed_charge: float | None = None
    bands: list[TariffBand] = []
    previous_to = 0.0

    for row in rows:
        scale = _cell(row, 3)
        unit = _normalize(str(_cell(row, 4)))
        value = _cell(row, 5)
        if _normalize(str(scale)) == "cargo fijo":
            fixed_charge = _number(value)
            continue
        if unit != "$/kwh" or not scale:
            continue
        label_text = _clean_band_label(str(scale))
        from_kwh, to_kwh = _band_bounds(label_text, previous_to)
        if to_kwh is not None:
            previous_to = to_kwh
        bands.append(
            TariffBand(
                label=label_text,
                from_kwh=from_kwh,
                to_kwh=to_kwh,
                price_ars_per_kwh=_number(value),
            )
        )

    if fixed_charge is None or not bands:
        raise TariffParseError(f"Incomplete residential XLSX category {label}")
    return TariffCategory(
        id=category_id,
        label=label,
        min_kwh=0,
        max_kwh=None,
        fixed_charge_ars=fixed_charge,
        bands=bands,
    )


def _residential_familiar_groups(rows: list[list[object]]) -> list[list[list[object]]]:
    starts: list[int] = []
    for index, row in enumerate(rows):
        category = _normalize(str(_cell(row, 2)))
        scale = _normalize(str(_cell(row, 3)))
        if category == "residencial" and scale == "cargo fijo":
            starts.append(index)

    groups: list[list[list[object]]] = []
    for position, start in enumerate(starts[:2]):
        end = starts[position + 1] if position + 1 < len(starts) else len(rows)
        groups.append(rows[start:end])
    return groups


def _xlsx_rows(content: bytes) -> list[list[object]]:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(BytesIO(content)) as archive:
        shared_strings = _shared_strings(archive, ns)
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[list[object]] = []
    for row in sheet.findall(".//a:row", ns):
        values: list[object] = []
        for cell in row.findall("a:c", ns):
            reference = cell.attrib.get("r", "")
            column = _column_index(reference)
            while len(values) <= column:
                values.append("")
            values[column] = _cell_value(cell, shared_strings, ns)
        rows.append(values)
    return rows


def _shared_strings(archive: ZipFile, ns: dict[str, str]) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("a:si", ns):
        strings.append("".join(text.text or "" for text in item.findall(".//a:t", ns)))
    return strings


def _cell_value(
    cell: ET.Element, shared_strings: list[str], ns: dict[str, str]
) -> object:
    value = cell.find("a:v", ns)
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        return shared_strings[int(value.text)]
    try:
        number = float(value.text)
    except ValueError:
        return value.text
    return int(number) if number.is_integer() else number


def _column_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        return 0
    index = 0
    for char in match.group(1):
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _cell(row: list[object], index: int) -> object:
    return row[index] if index < len(row) else ""


def _band_bounds(label: str, previous_to: float) -> tuple[float, float | None]:
    normalized = _normalize(label)
    first_match = re.search(r"(primeros|1ros\.?)\s+(\d+)", normalized)
    if first_match:
        return 0, float(first_match.group(2))

    next_match = re.search(r"(siguientes|stes\.?)\s+(\d+)", normalized)
    if next_match:
        amount = float(next_match.group(2))
        return previous_to, previous_to + amount

    excess_match = re.search(r"(excedente|exc\.?)\s+(?:de\s+)?(\d+)", normalized)
    if excess_match:
        return float(excess_match.group(2)), None

    return previous_to, None


def _clean_band_label(label: str) -> str:
    label = re.sub(r"cargo variable", "", label, flags=re.I)
    return _squash_spaces(label).strip(":- ")


def _numbers_from_text(text: str) -> list[float]:
    matches = re.findall(r"(?<!\d)(?:\d{1,3}(?:\.\d{3})*|\d+),\d+|\d+\.\d+", text)
    return [_number(match) for match in matches]


def _number(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    return float(text)


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
