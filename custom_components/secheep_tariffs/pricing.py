from __future__ import annotations

from dataclasses import dataclass

from .const import (
    PRICE_MODE_MANUAL_BAND,
    PRICE_MODE_MARGINAL,
    PRICE_MODE_PROFILE_NOT_CONFIGURED,
    SUBSIDY_PROFILE_N1,
    SUBSIDY_PROFILE_N2,
    SUBSIDY_PROFILE_N3,
    SUBSIDY_PROFILE_SEF,
)
from .models import NormalizedTariff, TariffBand, TariffCategory, TariffProfile


PROFILE_MAP = {
    SUBSIDY_PROFILE_N1: "residential_n1_no_subsidy",
    SUBSIDY_PROFILE_N2: "residential_sef",
    SUBSIDY_PROFILE_N3: "residential_sef",
    SUBSIDY_PROFILE_SEF: "residential_sef",
}


@dataclass(frozen=True)
class PriceResult:
    value: float | None
    mode: str
    profile: TariffProfile | None = None
    category: TariffCategory | None = None
    band: TariffBand | None = None
    reason: str | None = None


def current_price(
    tariff: NormalizedTariff | None,
    subsidy_profile: str,
    *,
    billing_cycle_kwh: float = 0,
    manual_band_index: int = 0,
) -> PriceResult:
    if tariff is None:
        return PriceResult(None, PRICE_MODE_PROFILE_NOT_CONFIGURED, reason="no_tariff")

    profile = select_profile(tariff, subsidy_profile)
    if profile is None:
        return PriceResult(
            None,
            PRICE_MODE_PROFILE_NOT_CONFIGURED,
            reason="subsidy_profile_not_configured",
        )

    category = first_category(profile)
    if category is None:
        return PriceResult(None, PRICE_MODE_PROFILE_NOT_CONFIGURED, profile=profile)

    if billing_cycle_kwh > 0:
        band = band_for_next_kwh(category, billing_cycle_kwh)
        if band is None:
            return PriceResult(None, PRICE_MODE_MARGINAL, profile, category)
        return PriceResult(
            band.price_ars_per_kwh, PRICE_MODE_MARGINAL, profile, category, band
        )

    if not category.bands:
        return PriceResult(None, PRICE_MODE_MANUAL_BAND, profile, category)
    band = category.bands[min(max(manual_band_index, 0), len(category.bands) - 1)]
    return PriceResult(
        band.price_ars_per_kwh, PRICE_MODE_MANUAL_BAND, profile, category, band
    )


def marginal_price(
    tariff: NormalizedTariff | None,
    subsidy_profile: str,
    billing_cycle_kwh: float,
) -> PriceResult:
    return current_price(
        tariff,
        subsidy_profile,
        billing_cycle_kwh=billing_cycle_kwh,
        manual_band_index=0,
    )


def average_variable_price(
    tariff: NormalizedTariff | None,
    subsidy_profile: str,
    billing_cycle_kwh: float,
) -> PriceResult:
    if tariff is None or billing_cycle_kwh <= 0:
        return PriceResult(None, "average", reason="billing_cycle_kwh_required")

    profile = select_profile(tariff, subsidy_profile)
    if profile is None:
        return PriceResult(None, "average", reason="subsidy_profile_not_configured")
    category = first_category(profile)
    if category is None:
        return PriceResult(None, "average", profile=profile)

    total = variable_charge_for_kwh(category, billing_cycle_kwh)
    band = band_for_kwh(category, billing_cycle_kwh)
    return PriceResult(total / billing_cycle_kwh, "average", profile, category, band)


def estimated_cycle_cost(
    tariff: NormalizedTariff | None,
    subsidy_profile: str,
    billing_cycle_kwh: float,
) -> PriceResult:
    average = average_variable_price(tariff, subsidy_profile, billing_cycle_kwh)
    if average.value is None or average.category is None:
        return PriceResult(None, "estimated_cycle_cost", reason=average.reason)
    return PriceResult(
        average.value * billing_cycle_kwh + average.category.fixed_charge_ars,
        "estimated_cycle_cost",
        average.profile,
        average.category,
        average.band,
    )


def select_profile(
    tariff: NormalizedTariff, subsidy_profile: str
) -> TariffProfile | None:
    profile_id = PROFILE_MAP.get(subsidy_profile)
    if profile_id is None:
        return None
    return next((profile for profile in tariff.profiles if profile.id == profile_id), None)


def first_category(profile: TariffProfile) -> TariffCategory | None:
    return profile.categories[0] if profile.categories else None


def band_for_kwh(category: TariffCategory, kwh: float) -> TariffBand | None:
    for band in category.bands:
        if kwh < band.from_kwh:
            continue
        if band.to_kwh is None or kwh <= band.to_kwh:
            return band
    return category.bands[-1] if category.bands else None


def band_for_next_kwh(category: TariffCategory, consumed_kwh: float) -> TariffBand | None:
    """Return rate for energy consumed after the current cycle total."""
    for band in category.bands:
        if consumed_kwh < band.from_kwh:
            continue
        if band.to_kwh is None or consumed_kwh < band.to_kwh:
            return band
    return category.bands[-1] if category.bands else None


def variable_charge_for_kwh(category: TariffCategory, kwh: float) -> float:
    remaining = kwh
    total = 0.0
    for band in category.bands:
        if remaining <= 0:
            break
        if band.to_kwh is None:
            width = remaining
        else:
            width = max(band.to_kwh - band.from_kwh, 0)
            width = min(width, remaining)
        total += width * band.price_ars_per_kwh
        remaining -= width
    return total
