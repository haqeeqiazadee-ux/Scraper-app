"""Vendor A: ingest catalog rows from a local CSV file."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

import pandas as pd
from dotenv import load_dotenv

from adapters.base_adapter import BaseVendorAdapter
from core.matcher import VendorProductInput


_LEADING_CURRENCY_RE = re.compile(r"^\s*\$?\s*")


def _csv_file_starts_like_html(path: str) -> bool:
    with open(path, "rb") as fh:
        head = fh.read(4096)
    if not head:
        return False
    h = head.lstrip().lower()
    if h.startswith(b"<!doctype") or h.startswith(b"<html"):
        return True
    if h.startswith(b"\xef\xbb\xbf"):
        low = head[:8192].lower()
        return b"<!doctype" in low or b"<html" in low
    return False


def _in_stock_only_from_env() -> bool:
    return (os.environ.get("VENDOR_A_IN_STOCK_ONLY") or "").strip().lower() in ("1", "true", "yes")


def _ingest_last_updated_from_env() -> datetime | None:
    """
    When feeds are fetched via ``run_feeds.py``, ``FEED_INGEST_TIMESTAMP_ISO`` is set (UTC).

    You can also set ``VENDOR_A_LAST_UPDATED_ISO`` or enable ``VENDOR_A_STAMP_INGEST=1`` for a local UTC stamp.
    """
    for key in ("VENDOR_A_LAST_UPDATED_ISO", "FEED_INGEST_TIMESTAMP_ISO"):
        raw = (os.environ.get(key) or "").strip()
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
    flag = (os.environ.get("VENDOR_A_STAMP_INGEST") or "").strip().lower()
    if flag in ("1", "true", "yes"):
        return datetime.now(timezone.utc)
    return None


def _read_vendor_csv(path: str) -> pd.DataFrame:
    """Load CSV/TSV or pipe-separated (e.g. SYNAXON ``ItemCode|MPN|...``); delimiter from the first line.

    Tries UTF-8 first, then CP1252 / Latin-1 so German vendor feeds (e.g. ä as 0xE4) decode cleanly.
    """
    if _csv_file_starts_like_html(path):
        raise RuntimeError(
            f"File {path!r} looks like HTML (e.g. a shop or login page), not CSV. "
            "Fix the feed URL or credentials so the download returns real catalog data."
        )
    with open(path, "rb") as fh:
        raw_first = fh.readline()
    if not raw_first:
        return pd.DataFrame()
    first = raw_first.decode("latin-1", errors="replace")
    pipes = first.count("|")
    tabs = first.count("\t")
    semi = first.count(";")
    comma = first.count(",")
    max_other = max(tabs, semi, comma)
    if pipes > max_other:
        sep = "|"
    elif tabs > semi and tabs > comma:
        sep = "\t"
    elif semi > comma:
        sep = ";"
    else:
        sep = ","
    read_kwargs: dict[str, Any] = {
        "sep": sep,
        "quotechar": '"',
        "engine": "python",
    }
    encodings = ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1")
    df: pd.DataFrame | None = None
    last_err: Exception | None = None
    for encoding in encodings:
        kwargs = {**read_kwargs, "encoding": encoding}
        try:
            try:
                df = pd.read_csv(path, **kwargs, on_bad_lines="skip")
            except TypeError:
                df = pd.read_csv(path, **kwargs)
            break
        except UnicodeDecodeError as e:
            last_err = e
            df = None
            continue
    if df is None:
        raise last_err if last_err else RuntimeError(f"Could not read CSV: {path!r}")
    df = df.dropna(axis=1, how="all")
    df.columns = [str(c).strip().strip('"').strip() for c in df.columns]
    return df


def _normalize_product_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map common column names to ``mpn``, ``brand``, and ``price``."""
    out = df.copy()
    cols = set(out.columns)

    if "OEMNR" in cols and "ARTICLENR" in cols:
        oem = out["OEMNR"].map(_strip_str)
        art = out["ARTICLENR"].map(_strip_str)
        out["mpn"] = oem.mask(oem.eq(""), art)
    elif "OEMNR" in cols:
        out = out.rename(columns={"OEMNR": "mpn"})
    elif "ARTICLENR" in cols:
        out = out.rename(columns={"ARTICLENR": "mpn"})
    elif "OEM Code" in cols and "AXRO Code" in cols:
        oem = out["OEM Code"].map(_strip_str)
        ax = out["AXRO Code"].map(_strip_str)
        out["mpn"] = oem.mask(oem.eq(""), ax)
    elif "OEM Code" in cols:
        out = out.rename(columns={"OEM Code": "mpn"})
    elif "AXRO Code" in cols:
        out = out.rename(columns={"AXRO Code": "mpn"})
    elif "PartNum" in cols:
        out = out.rename(columns={"PartNum": "mpn"})
    elif "MPN" in cols:
        out = out.rename(columns={"MPN": "mpn"})
    elif "Manufacturer Part Number" in cols:
        out = out.rename(columns={"Manufacturer Part Number": "mpn"})
    elif "Flex IT Part Number" in cols:
        out = out.rename(columns={"Flex IT Part Number": "mpn"})
    elif "Hersteller-Artikelnummer" in cols:
        out = out.rename(columns={"Hersteller-Artikelnummer": "mpn"})
    elif "Herstellerartikelnummer" in cols:
        out = out.rename(columns={"Herstellerartikelnummer": "mpn"})
    elif "ManProdNr" in cols:
        out = out.rename(columns={"ManProdNr": "mpn"})
    elif "ManuPartCode" in cols:
        out = out.rename(columns={"ManuPartCode": "mpn"})
    elif "ProdNr" in cols:
        out = out.rename(columns={"ProdNr": "mpn"})
    elif "Product Code" in cols:
        out = out.rename(columns={"Product Code": "mpn"})
    elif "ReferenceNo" in cols:
        out = out.rename(columns={"ReferenceNo": "mpn"})
    elif "ProductId" in cols:
        out = out.rename(columns={"ProductId": "mpn"})
    elif "ArtikelNr." in cols:
        out = out.rename(columns={"ArtikelNr.": "mpn"})
    elif "Art Nr." in cols:
        out = out.rename(columns={"Art Nr.": "mpn"})
    else:
        # Case-insensitive match for long vendor-specific headers
        lower_map = {str(c).strip().lower(): str(c).strip() for c in out.columns}
        for key in (
            "manufacturer part number",
            "mfr part number",
            "oem code",
            "axro code",
            "mpn",
            "manprodnr",
            "manupartcode",
            "manu part code",
            "flex it part number",
            "herstellerartikelnummer",
            "hersteller-artikelnummer",
            "artikelnummer",
            "prodnr",
            "product code",
            "referenceno",
            "reference no",
            "productid",
            "product id",
            "article number",
            "art nr.",
            "artikelnr.",
            "artnr",
        ):
            if key in lower_map:
                src = lower_map[key]
                out = out.rename(columns={src: "mpn"})
                break
        else:
            raise ValueError(
                "CSV needs a part-number column (e.g. PartNum, ARTICLENR, OEMNR, "
                "Manufacturer Part Number, Hersteller-Artikelnummer); "
                f"found {list(out.columns)!r}",
            )

    if "brand" not in out.columns:
        for old in ("BRAND", "Mfr", "Brand", "Manufacturer", "Hersteller", "Manuf_Name"):
            if old in out.columns:
                out = out.rename(columns={old: "brand"})
                break
    if "brand" not in out.columns:
        out["brand"] = ""

    if "price" not in out.columns:
        for old in (
            "PRICE",
            "PriceNet",
            "Price EURO",
            "TradePrice",
            "Wholesale",
            "Price",
            "RRP",
            "Sales Price",
            "Net Price",
            "Dealer Price",
            "Preis/€",
            "Preis/EUR",
            "Preis/Eur",
            "Preis",
            # Target Components Ltd qty-band list prices (1–4, 5–19, 20+)
            "1_4",
            "5_19",
            "20plus",
        ):
            if old in out.columns:
                out = out.rename(columns={old: "price"})
                break
    if "price" not in out.columns:
        for c in out.columns:
            cl = str(c).strip().lower()
            if cl.startswith("preis") or cl.startswith("price"):
                out = out.rename(columns={c: "price"})
                break

    missing = [c for c in ("mpn", "brand", "price") if c not in out.columns]
    if missing:
        raise ValueError(
            f"CSV missing normalized columns {missing}; columns were {list(out.columns)!r}",
        )
    return out


class VendorACsvAdapter(BaseVendorAdapter):
    """
    Reads CSV from ``VENDOR_A_CSV_PATH``.

    Supports **comma**, **semicolon**, **tab**, or **pipe** (``|``) separators. Maps PartNum/Mfr/Wholesale,
    ARTICLENR+OEMNR/BRAND/PRICE,
    Flex-IT ``Manufacturer Part Number``, or German MEMORYWORLD-style
    ``Hersteller-Artikelnummer`` / ``Hersteller`` / ``Preis/€`` / ``Bestand``.
    Systeam-style ``ArtikelNr.`` / ``Hersteller`` / ``Preis`` / ``Bestand J/N`` (Ja/Nein) / ``EAN-Nr``.
    AXRO-style ``OEM Code`` / ``AXRO Code`` / ``EAN Code`` / ``Stock`` / ``Price EURO``.
    SYNAXON-style ``MPN`` / ``Manufacturer`` / ``ItemName`` / ``Stock`` / ``PriceNet`` (pipe ``|``-delimited).
    Restock-style ``Product Code`` / ``Description`` / ``Quantity in Stock`` / ``Price``.
    TD SYNNEX-style tab-separated ``ManProdNr`` / ``Manuf_Name`` / ``TradePrice`` / ``currency_code`` /
    ``Stock`` / ``Product_Desc``.
    Target Components-style ``ManuPartCode`` / ``Manufacturer`` / qty-band ``1_4`` / ``5_19`` / ``20plus`` / ``Stock``.
    Alldis-style ``Herstellerartikelnummer`` / ``Preis`` / ``Bestand`` (no manufacturer column:
    set ``VENDOR_A_FALLBACK_BRAND`` or rows use ``Unknown`` for ``product.brand`` identity).
    Name from Description, Bezeichnung, Beschreibung, etc.

    When ``VENDOR_A_IN_STOCK_ONLY`` is set (default on stamped runs from ``run_feeds.py``), rows need a
    mapped stock column with value **> 0**; others are skipped. Rows with missing or non-positive **price**
    are always skipped.
    """

    _NAME_SOURCE_COLUMNS = (
        "ItemName",
        "Description",
        "DESCRIPTION",
        "Product_Desc",
        "Artikelbezeichnung",
        "Artikelbeschreibung",
        "Bezeichnung",
        "Beschreibung",
        "Name",
        "ProductName",
        "Title",
    )

    def __init__(self, csv_path: str | None = None) -> None:
        load_dotenv()
        self._path = csv_path or os.environ.get("VENDOR_A_CSV_PATH", "").strip()
        if not self._path:
            raise ValueError("VENDOR_A_CSV_PATH is not set in the environment or .env")

    def vendor_name(self) -> str:
        return os.environ.get("VENDOR_A_NAME", "Vendor A").strip() or "Vendor A"

    def load_items(self) -> Sequence[VendorProductInput]:
        df = _read_vendor_csv(self._path)
        if df.empty:
            return []

        df = _normalize_product_columns(df)

        name_col = self._resolve_name_column(df.columns)
        optional_int_map = {
            c: "stock_level"
            for c in (
                "Stock",
                "STOCK",
                "Qty",
                "OnHand",
                "Quantity",
                "Stock Quantity",
                "Quantity in Stock",
                "Bestand",
            )
            if c in df.columns
        }
        stock_jn_col = "Bestand J/N" if "Bestand J/N" in df.columns else None
        optional_cat_map: dict[str, str] = {}
        if "Category" in df.columns:
            optional_cat_map["Category"] = "category"
        elif "Warengruppe" in df.columns:
            optional_cat_map["Warengruppe"] = "category"
        elif "UNSPSCDESCRIPTION" in df.columns:
            optional_cat_map["UNSPSCDESCRIPTION"] = "category"
        elif "Classification" in df.columns:
            optional_cat_map["Classification"] = "category"

        stamp = _ingest_last_updated_from_env()
        items: list[VendorProductInput] = []
        fallback_brand = (os.environ.get("VENDOR_A_FALLBACK_BRAND") or "").strip()
        if not fallback_brand:
            fallback_brand = "Unknown"

        for row in df.to_dict(orient="records"):
            mpn = _strip_str(row.get("mpn"))
            brand = _strip_str(row.get("brand")) or fallback_brand
            price_f = _clean_price(row.get("price"))
            if not mpn or price_f is None or price_f <= 0:
                continue

            if name_col:
                title = _strip_str(row.get(name_col)) or mpn
            else:
                title = mpn

            ean_raw = (
                row.get("EANNR")
                or row.get("EAN")
                or row.get("EAN Code")
                or row.get("EAN-Nr")
            )
            ean = _strip_str(ean_raw) or None
            cur = _strip_str(row.get("CURRENCY") or row.get("currency_code")).upper()
            price_dec = Decimal(str(price_f))

            kwargs: dict[str, Any] = {
                "mpn": mpn,
                "brand": brand,
                "title": title,
                "ean": ean,
            }
            if cur == "GBP":
                kwargs["price_gbp"] = price_dec
                kwargs["region"] = "UK"
            elif cur == "USD":
                kwargs["price_usd"] = price_dec
                kwargs["region"] = "USA"
            else:
                kwargs["price_eur"] = price_dec
                kwargs["region"] = "EU"
            for src, dest in optional_int_map.items():
                v = _clean_int(row.get(src))
                if v is not None:
                    kwargs[dest] = v
            if stock_jn_col:
                sj = _stock_ja_nein(row.get(stock_jn_col))
                if sj is not None:
                    kwargs["stock_level"] = sj
            for src, dest in optional_cat_map.items():
                v = _strip_str(row.get(src))
                if v:
                    kwargs[dest] = v
            if stamp is not None:
                kwargs["last_updated"] = stamp

            if _in_stock_only_from_env():
                sl = kwargs.get("stock_level")
                if sl is None or int(sl) <= 0:
                    continue

            items.append(VendorProductInput(**kwargs))
        return items

    def _resolve_name_column(self, columns: pd.Index) -> str | None:
        cols = set(str(c) for c in columns)
        for cand in self._NAME_SOURCE_COLUMNS:
            if cand in cols:
                return cand
        return None


def _strip_str(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _clean_price(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    s = _LEADING_CURRENCY_RE.sub("", s)
    # EU/German: 1.234,56 (thousands .) or 12,99 (decimal ,)
    if re.search(r",\d{1,2}\s*$", s):
        if "." in s:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _stock_ja_nein(value: Any) -> int | None:
    """Systeam ``Bestand J/N``: J/Ja → in stock (1), N/Nein → 0."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().upper()
    if not s or s in ("NAN", "NONE", "-", "—"):
        return None
    if s in ("J", "JA", "Y", "YES", "1", "T", "TRUE"):
        return 1
    if s in ("N", "NEIN", "NO", "0", "F", "FALSE"):
        return 0
    return _clean_int(value)


def _clean_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None
