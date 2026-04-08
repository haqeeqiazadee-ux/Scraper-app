"""Fixed multi-currency conversion: derive GBP, EUR, USD from one source price using ``.env`` factors."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import lru_cache

from dotenv import load_dotenv

_Q4 = Decimal("0.0001")


def _parse_rate(key: str, default: str) -> Decimal:
    load_dotenv()
    raw = (os.environ.get(key) or default).strip()
    try:
        d = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{key} must be a positive decimal, got {raw!r}") from exc
    if d <= 0:
        raise ValueError(f"{key} must be > 0, got {d}")
    return d


@lru_cache
def fx_gbp_per_eur() -> Decimal:
    """GBP amount for one EUR: ``gbp = eur * fx_gbp_per_eur()``."""
    return _parse_rate("B2B_FX_GBP_PER_EUR", "0.86")


@lru_cache
def fx_usd_per_eur() -> Decimal:
    """USD amount for one EUR: ``usd = eur * fx_usd_per_eur()``."""
    return _parse_rate("B2B_FX_USD_PER_EUR", "1.08")


def _q4(d: Decimal) -> Decimal:
    return d.quantize(_Q4, rounding=ROUND_HALF_UP)


def triplet_prices(
    price_gbp: Decimal | None,
    price_eur: Decimal | None,
    price_usd: Decimal | None,
    region: str,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    From the feed's single-currency line (and ``region``), compute all three amounts.

    Pivot: EUR. Env:

    - ``B2B_FX_GBP_PER_EUR`` — multiply EUR → GBP
    - ``B2B_FX_USD_PER_EUR`` — multiply EUR → USD

    Canonical source: region **UK** uses GBP, **EU** uses EUR, **USA** uses USD; if that
    column is missing, falls back to any set price (EUR, then GBP, then USD).
    """
    r = (region or "EU").strip().upper()
    if r not in {"UK", "EU", "USA"}:
        r = "EU"

    g = fx_gbp_per_eur()
    u = fx_usd_per_eur()

    eur: Decimal | None = None
    if r == "UK" and price_gbp is not None:
        eur = price_gbp / g
    elif r == "USA" and price_usd is not None:
        eur = price_usd / u
    elif r == "EU" and price_eur is not None:
        eur = price_eur
    else:
        if price_eur is not None:
            eur = price_eur
        elif price_gbp is not None:
            eur = price_gbp / g
        elif price_usd is not None:
            eur = price_usd / u

    if eur is None:
        raise ValueError("need at least one of price_gbp, price_eur, price_usd")

    out_eur = _q4(eur)
    out_gbp = _q4(eur * g)
    out_usd = _q4(eur * u)
    return out_gbp, out_eur, out_usd


def clear_fx_cache() -> None:
    """For tests / reload env."""
    fx_gbp_per_eur.cache_clear()
    fx_usd_per_eur.cache_clear()
