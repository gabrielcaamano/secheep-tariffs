from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import NormalizedTariff


@dataclass(frozen=True)
class StoredTariff:
    tariff: NormalizedTariff
    fetched_at: datetime
    source_status: str
    primary_effective_date: str | None
    primary_source_url: str | None
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "tariff": self.tariff.as_dict(),
            "fetched_at": self.fetched_at.isoformat(),
            "source_status": self.source_status,
            "primary_effective_date": self.primary_effective_date,
            "primary_source_url": self.primary_source_url,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoredTariff":
        return cls(
            tariff=NormalizedTariff.from_dict(data["tariff"]),
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            source_status=data.get("source_status", "cached"),
            primary_effective_date=data.get("primary_effective_date"),
            primary_source_url=data.get("primary_source_url"),
            error=data.get("error"),
        )


class TariffStore:
    def __init__(self, hass) -> None:
        from homeassistant.helpers.storage import Store

        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(self) -> StoredTariff | None:
        data = await self._store.async_load()
        if not data:
            return None
        return StoredTariff.from_dict(data)

    async def async_save(self, stored: StoredTariff) -> None:
        await self._store.async_save(stored.as_dict())
