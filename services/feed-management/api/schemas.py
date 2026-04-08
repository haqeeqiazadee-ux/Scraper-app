"""Pydantic response/request shapes for the public API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VendorOfferPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_name: str
    region: str
    price_gbp: Decimal | None
    price_eur: Decimal | None
    price_usd: Decimal | None
    stock_level: int | None
    last_updated: datetime


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mpn: str
    brand: str
    title: str
    category: str | None = None
    ean: str | None = None


class ProductDetail(ProductSummary):
    asin: str | None = None
    amazon_monthly_sales: int | None = None
    amazon_url: str | None = None
    offers: list[VendorOfferPublic] = Field(default_factory=list)


class ProductListResponse(BaseModel):
    items: list[ProductSummary]
    offset: int
    limit: int
    has_more: bool


class OfferListResponse(BaseModel):
    items: list[VendorOfferPublic]
    offset: int
    limit: int
    has_more: bool


class SupplierListResponse(BaseModel):
    vendors: list[str]


class HealthResponse(BaseModel):
    ok: bool
    database: str
