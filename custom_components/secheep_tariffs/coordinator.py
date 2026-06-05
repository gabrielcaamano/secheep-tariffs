from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from aiohttp import ClientConnectorCertificateError, ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    FALLBACK_SOURCE_URL,
    SOURCE_URL,
)
from .models import NormalizedTariff
from .parser import (
    ScannedPdfError,
    TariffParseError,
    parse_pdf_tariff,
    parse_xlsx_tariff,
)
from .source import (
    TariffSourceDocument,
    parse_argentina_source_index,
    parse_secheep_source_index,
    select_primary_tariff_document,
)
from .storage import StoredTariff, TariffStore

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecheepTariffData:
    tariff: NormalizedTariff | None
    fetched_at: datetime | None
    source_status: str
    data_current: bool
    active_source_url: str | None
    active_effective_date: str | None
    primary_source_url: str | None
    primary_effective_date: str | None
    error: str | None


class SecheepTariffCoordinator(DataUpdateCoordinator):
    """Fetch, parse, cache, and expose SECHEEP tariff data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_SCAN_INTERVAL_HOURS),
        )
        self.entry = entry
        self._session = async_get_clientsession(hass)
        self._store = TariffStore(hass)
        self._cached: StoredTariff | None = None

    async def _async_update_data(self) -> SecheepTariffData:
        if self._cached is None:
            self._cached = await self._store.async_load()

        primary_document: TariffSourceDocument | None = None
        primary_error: str | None = None

        try:
            primary_document = await self._async_primary_document()
            if primary_document is None:
                raise TariffParseError("No SECHEEP tariff document found")
            tariff = await self._async_parse_document(primary_document)
            return await self._async_store_success(
                tariff,
                source_status="primary",
                primary_document=primary_document,
                error=None,
            )
        except (ClientError, OSError, ScannedPdfError, TariffParseError) as err:
            primary_error = f"{type(err).__name__}: {err}"
            _LOGGER.warning("SECHEEP primary tariff source failed: %s", primary_error)

        try:
            fallback_document = await self._async_fallback_document()
            if fallback_document is None:
                raise TariffParseError("No fallback tariff document found")
            tariff = await self._async_parse_document(fallback_document)
            return await self._async_store_success(
                tariff,
                source_status="fallback",
                primary_document=primary_document,
                error=primary_error,
            )
        except (ClientError, OSError, TariffParseError) as err:
            fallback_error = f"{type(err).__name__}: {err}"
            _LOGGER.warning("SECHEEP fallback tariff source failed: %s", fallback_error)

        if self._cached is not None:
            return self._from_stored(
                self._cached,
                "cached",
                f"{primary_error}; fallback failed: {fallback_error}",
            )

        return SecheepTariffData(
            tariff=None,
            fetched_at=None,
            source_status="failed",
            data_current=False,
            active_source_url=None,
            active_effective_date=None,
            primary_source_url=primary_document.url if primary_document else None,
            primary_effective_date=(
                primary_document.effective_date.isoformat()
                if primary_document is not None
                else None
            ),
            error=f"{primary_error}; fallback failed: {fallback_error}",
        )

    async def _async_primary_document(self) -> TariffSourceDocument | None:
        html = await self._async_fetch_text(SOURCE_URL)
        return select_primary_tariff_document(parse_secheep_source_index(html, SOURCE_URL))

    async def _async_fallback_document(self) -> TariffSourceDocument | None:
        html = await self._async_fetch_text(FALLBACK_SOURCE_URL)
        return select_primary_tariff_document(
            parse_argentina_source_index(html, FALLBACK_SOURCE_URL)
        )

    async def _async_parse_document(
        self, document: TariffSourceDocument
    ) -> NormalizedTariff:
        content = await self._async_fetch_bytes(document.url)
        if document.is_xlsx:
            return parse_xlsx_tariff(
                content,
                source_url=document.url,
                effective_date=document.effective_date,
            )
        if document.is_pdf:
            return parse_pdf_tariff(
                content,
                source_url=document.url,
                effective_date=document.effective_date,
            )
        raise TariffParseError(f"Unsupported tariff document: {document.url}")

    async def _async_fetch_text(self, url: str) -> str:
        async with self._session.get(url, timeout=30) as response:
            response.raise_for_status()
            return await response.text()

    async def _async_fetch_bytes(self, url: str) -> bytes:
        try:
            return await self._async_fetch_bytes_once(url)
        except ClientConnectorCertificateError:
            if url.startswith("https://www.energia.gob.ar/"):
                return await self._async_fetch_bytes_once(
                    url.replace("https://", "http://", 1)
                )
            raise

    async def _async_fetch_bytes_once(self, url: str) -> bytes:
        async with self._session.get(url, timeout=60) as response:
            response.raise_for_status()
            return await response.read()

    async def _async_store_success(
        self,
        tariff: NormalizedTariff,
        *,
        source_status: str,
        primary_document: TariffSourceDocument | None,
        error: str | None,
    ) -> SecheepTariffData:
        stored = StoredTariff(
            tariff=tariff,
            fetched_at=datetime.now(timezone.utc),
            source_status=source_status,
            primary_effective_date=(
                primary_document.effective_date.isoformat()
                if primary_document is not None
                else None
            ),
            primary_source_url=primary_document.url if primary_document else None,
            error=error,
        )
        await self._store.async_save(stored)
        self._cached = stored
        return self._from_stored(stored, source_status, error)

    def _from_stored(
        self, stored: StoredTariff, source_status: str, error: str | None
    ) -> SecheepTariffData:
        primary_effective_date = stored.primary_effective_date
        data_current = True
        if primary_effective_date is not None:
            data_current = stored.tariff.effective_date.isoformat() >= primary_effective_date
        return SecheepTariffData(
            tariff=stored.tariff,
            fetched_at=stored.fetched_at,
            source_status=source_status,
            data_current=data_current and source_status == "primary",
            active_source_url=stored.tariff.source_url,
            active_effective_date=stored.tariff.effective_date.isoformat(),
            primary_source_url=stored.primary_source_url,
            primary_effective_date=primary_effective_date,
            error=error or stored.error,
        )
