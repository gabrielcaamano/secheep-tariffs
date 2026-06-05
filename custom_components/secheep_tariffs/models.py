from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TariffBand:
    """One kWh range inside a SECHEEP category."""

    label: str
    from_kwh: float
    to_kwh: float | None
    price_ars_per_kwh: float
    components: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TariffCategory:
    """SECHEEP category and its fixed/variable charges."""

    id: str
    label: str
    min_kwh: float | None
    max_kwh: float | None
    fixed_charge_ars: float
    bands: list[TariffBand]


@dataclass(frozen=True)
class TariffProfile:
    """Residential tariff variant exposed to Home Assistant."""

    id: str
    name: str
    subsidy: str
    categories: list[TariffCategory]


@dataclass(frozen=True)
class BillingPeriod:
    """Billing period metadata."""

    type: str = "monthly"
    days: int | None = None


@dataclass(frozen=True)
class NormalizedTariff:
    """Normalized SECHEEP tariff data safe to cache as JSON."""

    provider: str
    service_area: str
    effective_date: date
    source_url: str
    resolution: str | None
    currency: str
    billing_period: BillingPeriod
    profiles: list[TariffProfile]
    schema_version: int = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["effective_date"] = self.effective_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NormalizedTariff":
        return cls(
            provider=data["provider"],
            service_area=data["service_area"],
            effective_date=date.fromisoformat(data["effective_date"]),
            source_url=data["source_url"],
            resolution=data.get("resolution"),
            currency=data["currency"],
            billing_period=BillingPeriod(**data["billing_period"]),
            profiles=[
                TariffProfile(
                    id=profile["id"],
                    name=profile["name"],
                    subsidy=profile["subsidy"],
                    categories=[
                        TariffCategory(
                            id=category["id"],
                            label=category["label"],
                            min_kwh=category.get("min_kwh"),
                            max_kwh=category.get("max_kwh"),
                            fixed_charge_ars=category["fixed_charge_ars"],
                            bands=[
                                TariffBand(
                                    label=band["label"],
                                    from_kwh=band["from_kwh"],
                                    to_kwh=band.get("to_kwh"),
                                    price_ars_per_kwh=band["price_ars_per_kwh"],
                                    components=band.get("components", {}),
                                )
                                for band in category["bands"]
                            ],
                        )
                        for category in profile["categories"]
                    ],
                )
                for profile in data["profiles"]
            ],
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )
