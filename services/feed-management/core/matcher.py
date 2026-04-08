"""Match vendor catalog lines to ``products`` and merge into ``vendor_offers``."""

from __future__ import annotations

import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Callable, Mapping, Sequence, TypeVar

from sqlalchemy import delete, insert, select, text, tuple_, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from core.database import MasterIncompleteRow, MasterProduct, Product, VendorOffer
from core.price_fx import triplet_prices

_REGIONS = frozenset({"UK", "EU", "USA"})
_MAX_TITLE_WORDS = 15


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes")
# PHP ``b2b_master_cleanup_strip_text`` parity: letters/digits (Unicode), spaces, safe punctuation.
_MASTER_STRIP_DISALLOW = re.compile(r"[^\w\s\-_.\/:&(),\']", re.UNICODE)


def _master_cleanup_strip_text(s: str) -> str:
    """Strip junk characters from master text (parity with ``index.php`` cleanup)."""
    if not s:
        return ""
    s = s.replace("?", "")
    s = _MASTER_STRIP_DISALLOW.sub("", s)
    return re.sub(r"\s+", " ", s.strip()).strip()


def _clamp_title_words(title: str, max_words: int = _MAX_TITLE_WORDS) -> str:
    """First ``max_words`` words; Unicode whitespace (PHP ``preg_split('/\\s+/u')`` parity)."""
    if max_words < 1:
        return ""
    parts = [p for p in re.split(r"\s+", title.strip(), flags=re.UNICODE) if p]
    if len(parts) <= max_words:
        return " ".join(parts)
    return " ".join(parts[:max_words])


def normalize_master_row_texts(
    mpn: str,
    brand: str,
    title: str,
    category: str | None,
) -> tuple[str, str, str, str | None]:
    """
    Apply master cleanup before insert: strip MPN/Brand/Title/Category; clamp title to 15 words.
    If stripping empties MPN or Brand but the trimmed original had content, keep the original (PHP parity).
    """
    om = mpn.strip()
    ob = brand.strip()
    ot = title.strip()
    oc = (category or "").strip()

    nm = _master_cleanup_strip_text(om)
    if not nm:
        nm = om
    nb = _master_cleanup_strip_text(ob)
    if not nb:
        nb = ob
    nt = _master_cleanup_strip_text(ot)
    if not oc:
        ncat = None
    else:
        ncat_raw = _master_cleanup_strip_text(oc)
        ncat = ncat_raw if ncat_raw else None

    t = _clamp_title_words(nt)
    if not t:
        t = _clamp_title_words(f"{nm} {nb}".strip())
    if not t:
        t = "Product"

    return nm, nb, t, ncat


def soft_strip_master_field(value: str | None) -> str | None:
    """Strip for incomplete-queue rows; preserve original if strip wipes a non-empty field."""
    if value is None:
        return None
    o = str(value).strip()
    if not o:
        return None
    c = _master_cleanup_strip_text(o)
    return o if not c else c


@dataclass(frozen=True, slots=True)
class VendorProductInput:
    """One vendor line item (MPN + brand identify the canonical product)."""

    mpn: str
    brand: str
    title: str
    region: str = "EU"
    price_gbp: Decimal | None = None
    price_eur: Decimal | None = None
    price_usd: Decimal | None = None
    ean: str | None = None
    category: str | None = None
    stock_level: int | None = None
    last_updated: datetime | None = None


def _to_decimal(value: Decimal | str | float | int) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise TypeError(f"price must be convertible to Decimal, got {value!r}") from exc


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return _to_decimal(value)


def _normalize_region(value: Any) -> str:
    r = str(value or "EU").strip().upper()
    return r if r in _REGIONS else "EU"


def _resolve_prices(row: Mapping[str, Any]) -> tuple[Decimal | None, Decimal | None, Decimal | None, str]:
    """Map legacy ``price`` / ``currency`` or explicit ``price_*`` columns."""
    pg = _optional_decimal(row.get("price_gbp"))
    pe = _optional_decimal(row.get("price_eur"))
    pu = _optional_decimal(row.get("price_usd"))
    region = _normalize_region(row.get("region"))
    if pg is not None or pe is not None or pu is not None:
        return pg, pe, pu, region
    if "price" not in row:
        return None, None, None, region
    p = _to_decimal(row["price"])
    cur = str(row.get("currency") or row.get("CURRENCY") or "").strip().upper()
    if cur in ("GBP",):
        return p, None, None, "UK"
    if cur in ("USD", "US", "US$"):
        return None, None, p, "USA"
    return None, p, None, "EU"


def _coerce_row(row: VendorProductInput | Mapping[str, Any]) -> VendorProductInput:
    if isinstance(row, VendorProductInput):
        r = row.region.strip().upper()
        if r not in _REGIONS:
            r = "EU"
        if row.price_gbp is None and row.price_eur is None and row.price_usd is None:
            raise ValueError("VendorProductInput requires at least one of price_gbp, price_eur, price_usd")
        if r == row.region:
            return row
        return VendorProductInput(
            mpn=row.mpn,
            brand=row.brand,
            title=row.title,
            region=r,
            price_gbp=row.price_gbp,
            price_eur=row.price_eur,
            price_usd=row.price_usd,
            ean=row.ean,
            category=row.category,
            stock_level=row.stock_level,
            last_updated=row.last_updated,
        )
    try:
        title = row.get("title") or row.get("name")
        if title is None:
            raise KeyError("title")
        category = row.get("category")
        stock = row.get("stock_level")
        lu = row.get("last_updated")
        ean = row.get("ean")
        pg, pe, pu, region = _resolve_prices(row)
        if pg is None and pe is None and pu is None:
            raise ValueError("at least one of price_gbp, price_eur, price_usd, or price is required")
        return VendorProductInput(
            mpn=str(row["mpn"]),
            brand=str(row["brand"]),
            title=str(title),
            region=region,
            price_gbp=pg,
            price_eur=pe,
            price_usd=pu,
            ean=None if ean is None else str(ean).strip() or None,
            category=None if category is None else str(category),
            stock_level=None if stock is None else int(stock),
            last_updated=lu,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid vendor row mapping: {row!r}") from exc


def _normalize_key(mpn: str, brand: str) -> tuple[str, str]:
    m = mpn.strip()
    b = brand.strip()
    if not m or not b:
        raise ValueError("mpn and brand must be non-empty after stripping")
    return m, b


def _identity_key(mpn: str, brand: str) -> tuple[str, str]:
    """Key for maps / dedup; matches typical MySQL ``utf8mb4_*_ci`` uniqueness (case-insensitive)."""
    m, b = _normalize_key(mpn, brand)
    return (m.casefold(), b.casefold())


@dataclass(slots=True)
class _PreparedItem:
    mpn: str
    brand: str
    title: str
    category: str | None
    ean: str | None
    region: str
    price_gbp: Decimal | None
    price_eur: Decimal | None
    price_usd: Decimal | None
    stock_level: int | None
    last_updated: datetime | None


def _prepare_items(
    items: Sequence[VendorProductInput | Mapping[str, Any]],
) -> list[_PreparedItem]:
    """Strip fields; last row wins per logical product (MPN + brand, case-insensitive brand/mpn)."""
    by_key: dict[tuple[str, str], _PreparedItem] = {}
    for raw in items:
        row = _coerce_row(raw)
        mpn, brand = _normalize_key(row.mpn, row.brand)
        ikey = _identity_key(mpn, brand)
        title = _clamp_title_words(row.title.strip())
        if not title:
            raise ValueError("title must be non-empty after stripping")
        if row.price_gbp is None and row.price_eur is None and row.price_usd is None:
            raise ValueError("at least one of price_gbp, price_eur, price_usd is required")
        cat = row.category.strip() if row.category else None
        if cat == "":
            cat = None
        ean = row.ean.strip() if row.ean else None
        if ean == "":
            ean = None
        pg, pe, pu = triplet_prices(row.price_gbp, row.price_eur, row.price_usd, row.region)
        by_key[ikey] = _PreparedItem(
            mpn=mpn,
            brand=brand,
            title=title,
            category=cat,
            ean=ean,
            region=row.region,
            price_gbp=pg,
            price_eur=pe,
            price_usd=pu,
            stock_level=row.stock_level,
            last_updated=row.last_updated,
        )
    return list(by_key.values())


_PRICE_Q4 = Decimal("0.0001")


def _decimal_field_eq(a: Decimal | None, b: Decimal | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.quantize(_PRICE_Q4, rounding=ROUND_HALF_UP) == b.quantize(_PRICE_Q4, rounding=ROUND_HALF_UP)


def _vendor_offer_matches_prepared(offer: VendorOffer, p: _PreparedItem) -> bool:
    if not _decimal_field_eq(offer.price_gbp, p.price_gbp):
        return False
    if not _decimal_field_eq(offer.price_eur, p.price_eur):
        return False
    if not _decimal_field_eq(offer.price_usd, p.price_usd):
        return False
    return offer.stock_level == p.stock_level


_T = TypeVar("_T")


def _chunks(seq: Sequence[_T], size: int) -> list[list[_T]]:
    if size < 1:
        raise ValueError("chunk_size must be >= 1")
    return [list(seq[i : i + size]) for i in range(0, len(seq), size)]


def _parse_amazon_monthly_sales(val: Any) -> int | None:
    if val is None or val == "":
        return None
    s = str(val).strip().replace(",", "").replace(" ", "")
    if not s or s.lower() in {"nan", "none"}:
        return None
    try:
        v = int(Decimal(s))
    except (InvalidOperation, ValueError, TypeError):
        try:
            v = int(float(s))
        except (ValueError, TypeError):
            return None
    return v if v >= 0 else None


def _norm_asin(val: Any) -> str | None:
    if val is None or val == "":
        return None
    s = str(val).strip().upper()
    if not s or s.lower() == "nan":
        return None
    return s[:20] if len(s) > 20 else s


def _norm_amazon_url(val: Any) -> str | None:
    if val is None or val == "":
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    return s[:1024] if len(s) > 1024 else s


_ASIN_URL_QUERY = re.compile(r"[?&]asin=([A-Z0-9]{10})\b", re.I)
_ASIN_URL_PATH = re.compile(
    r"/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:[/\?#]|$)",
    re.I,
)
_ASIN_URL_LEGACY = re.compile(r"/(?:exec/obidos/ASIN/|o/ASIN/)([A-Z0-9]{10})", re.I)
_AMAZON_HOST = re.compile(r"amazon\.|amzn\.", re.I)


def _asin_from_amazon_url(url: str | None) -> str | None:
    """10-char ASIN from product page URL (parity with ``b2b_asin_from_amazon_url`` in PHP)."""
    if not url or not str(url).strip():
        return None
    u = str(url).strip()
    if not _AMAZON_HOST.search(u):
        return None
    m = _ASIN_URL_QUERY.search(u)
    if m:
        return m.group(1).upper()
    m = _ASIN_URL_PATH.search(u)
    if m:
        return m.group(1).upper()
    m = _ASIN_URL_LEGACY.search(u)
    if m:
        return m.group(1).upper()
    return None


def _sync_catalog_from_master_ids(
    session: Session,
    master_ids: Sequence[int],
    *,
    chunk_size: int,
    commit_each_chunk: bool = False,
) -> tuple[int, int]:
    """Update matching ``products`` from ``master_products`` and insert missing catalog rows (PHP parity)."""
    ids = sorted({int(i) for i in master_ids if int(i) > 0})
    if not ids:
        return 0, 0
    updated = 0
    inserted = 0
    for chunk in _chunks(ids, chunk_size):
        id_list = ",".join(str(i) for i in chunk)
        up = session.execute(
            text(
                "UPDATE products p INNER JOIN master_products m "
                "ON LOWER(TRIM(p.mpn)) = LOWER(TRIM(m.mpn)) AND LOWER(TRIM(p.brand)) = LOWER(TRIM(m.brand)) "
                "SET p.title = m.title, p.ean = m.ean, p.category = m.category, "
                "p.asin = m.asin, p.amazon_monthly_sales = m.amazon_monthly_sales, p.amazon_url = m.amazon_url "
                f"WHERE m.id IN ({id_list})",
            ),
        )
        updated += int(up.rowcount or 0)
        ins = session.execute(
            text(
                "INSERT INTO products (mpn, brand, title, ean, category, asin, amazon_monthly_sales, amazon_url) "
                "SELECT m.mpn, m.brand, m.title, m.ean, m.category, m.asin, m.amazon_monthly_sales, m.amazon_url "
                "FROM master_products m "
                f"WHERE m.id IN ({id_list}) "
                "AND NOT EXISTS (SELECT 1 FROM products p WHERE "
                "LOWER(TRIM(p.mpn)) = LOWER(TRIM(m.mpn)) AND LOWER(TRIM(p.brand)) = LOWER(TRIM(m.brand)))",
            ),
        )
        inserted += int(ins.rowcount or 0)
        if commit_each_chunk:
            session.commit()
    return updated, inserted


def _master_row_identity(mpn: str, brand: str) -> tuple[str, str]:
    """Match ``SELECT LOWER(TRIM(...))`` semantics for ASCII-heavy B2B SKUs (PHP / MySQL parity)."""
    return (mpn.strip().lower(), brand.strip().lower())


def _load_master_identity_keys(session: Session) -> set[tuple[str, str]]:
    rows = session.execute(
        text("SELECT LOWER(TRIM(mpn)), LOWER(TRIM(brand)) FROM master_products"),
    ).all()
    return {((a or "").lower(), (b or "").lower()) for a, b in rows}


def _load_master_key_to_id(session: Session) -> dict[tuple[str, str], int]:
    """Map the same identity as :func:`_load_master_identity_keys` (MySQL ``LOWER(TRIM(...))``) to ``master_products.id``."""
    rows = session.execute(
        text("SELECT id, LOWER(TRIM(mpn)), LOWER(TRIM(brand)) FROM master_products"),
    ).all()
    m: dict[tuple[str, str], int] = {}
    for rid, ka, kb in rows:
        k = ((ka or "").lower(), (kb or "").lower())
        m[k] = int(rid)
    return m


def _master_mpn_update_conflicts(session: Session, row_id: int, brand: str, mpn: str) -> bool:
    """Another row already uses this normalized MPN+Brand (excluding ``row_id``)."""
    r = session.execute(
        text(
            "SELECT 1 FROM master_products WHERE id <> :id "
            "AND LOWER(TRIM(brand)) = LOWER(TRIM(:b)) AND LOWER(TRIM(mpn)) = LOWER(TRIM(:m)) LIMIT 1",
        ),
        {"id": row_id, "b": brand, "m": mpn},
    ).first()
    return r is not None


def _products_catalog_identity_taken_elsewhere(
    session: Session,
    *,
    new_mpn: str,
    new_brand: str,
    old_mpn: str,
    old_brand: str,
) -> bool:
    """
    Another ``products`` row already has (``new_mpn``, ``new_brand``).

    Without this check, ``UPDATE products SET mpn=…`` can raise ``1062`` on ``uq_products_mpn_brand`` when
    the master snapshot did not list a conflicting ``master_products`` row (e.g. catalog-only duplicate).
    """
    r = session.execute(
        text(
            "SELECT 1 FROM products WHERE "
            "LOWER(TRIM(mpn)) = LOWER(TRIM(:nm)) AND LOWER(TRIM(brand)) = LOWER(TRIM(:nb)) "
            "AND NOT (LOWER(TRIM(mpn)) = LOWER(TRIM(:om)) AND LOWER(TRIM(brand)) = LOWER(TRIM(:ob))) "
            "LIMIT 1",
        ),
        {"nm": new_mpn, "nb": new_brand, "om": old_mpn, "ob": old_brand},
    ).first()
    return r is not None


def _nullable_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _db_str_blank(val: Any) -> bool:
    if val is None:
        return True
    return str(val).strip() == ""


def _is_mysql_lock_wait_timeout(exc: BaseException) -> bool:
    """InnoDB ``1205`` — often from long transactions or concurrent web jobs on shared hosting."""
    s = str(exc)
    if "1205" in s and ("lock" in s.lower() or "HY000" in s):
        return True
    orig = getattr(exc, "orig", None)
    if orig is not None and getattr(orig, "errno", None) == 1205:
        return True
    return False


def _patch_row_writes_retry(
    session: Session,
    *,
    products_ops: Sequence[tuple[Any, Mapping[str, Any]]] = (),
    master_stmt: Any,
    master_params: Mapping[str, Any],
    max_attempts: int = 8,
    base_delay_sec: float = 0.06,
) -> None:
    """Run ``products`` UPDATEs (if any) then ``master_products``; retry chain on MySQL ``1205``."""
    for attempt in range(max_attempts):
        try:
            for stmt, params in products_ops:
                session.execute(stmt, params)
            session.execute(master_stmt, master_params)
            return
        except Exception as e:
            if not _is_mysql_lock_wait_timeout(e) or attempt >= max_attempts - 1:
                raise
            session.rollback()
            time.sleep(base_delay_sec * (2**attempt))


@dataclass
class _MasterPatchIndex:
    """In-memory snapshot for fast identifier-patch matching (avoids per-row SQL)."""

    by_id: dict[int, dict[str, Any]]
    ean_to_ids: dict[str, list[int]]
    mpn_to_ids: dict[str, list[int]]
    mpn_brand_to_ids: dict[tuple[str, str], list[int]]
    asin_to_ids: dict[str, list[int]]
    brand_mpn_to_ids: dict[tuple[str, str], list[int]]


def _load_master_patch_index(session: Session) -> _MasterPatchIndex:
    rows = session.execute(
        text(
            "SELECT id, mpn, brand, title, category, ean, asin, amazon_url, amazon_monthly_sales "
            "FROM master_products",
        ),
    ).all()
    by_id: dict[int, dict[str, Any]] = {}
    ean_to_ids: dict[str, list[int]] = defaultdict(list)
    mpn_to_ids: dict[str, list[int]] = defaultdict(list)
    mpn_brand_to_ids: dict[tuple[str, str], list[int]] = defaultdict(list)
    asin_to_ids: dict[str, list[int]] = defaultdict(list)
    brand_mpn_to_ids: dict[tuple[str, str], list[int]] = defaultdict(list)

    for rid, mpn, brand, title, category, ean, asin, url, ams in rows:
        mid = int(rid)
        by_id[mid] = {
            "mpn": mpn,
            "brand": brand,
            "title": title,
            "category": category,
            "ean": ean,
            "asin": asin,
            "amazon_url": url,
            "amazon_monthly_sales": ams,
        }
        es = str(ean).strip() if ean is not None else ""
        if es:
            ean_to_ids[es].append(mid)
        lm = (str(mpn).strip()).lower() if mpn is not None else ""
        lb = (str(brand).strip()).lower() if brand is not None else ""
        if lm:
            mpn_to_ids[lm].append(mid)
        if lm and lb:
            mpn_brand_to_ids[(lm, lb)].append(mid)
        au = str(asin).strip().upper() if asin is not None and str(asin).strip() else ""
        if au:
            asin_to_ids[au].append(mid)
        if lb and lm:
            brand_mpn_to_ids[(lb, lm)].append(mid)

    def _freeze(m: dict[str, list[int]]) -> dict[str, list[int]]:
        return {k: list(v) for k, v in m.items()}

    def _freeze2(m: dict[tuple[str, str], list[int]]) -> dict[tuple[str, str], list[int]]:
        return {k: list(v) for k, v in m.items()}

    return _MasterPatchIndex(
        by_id=by_id,
        ean_to_ids=_freeze(ean_to_ids),
        mpn_to_ids=_freeze(mpn_to_ids),
        mpn_brand_to_ids=_freeze2(mpn_brand_to_ids),
        asin_to_ids=_freeze(asin_to_ids),
        brand_mpn_to_ids=_freeze2(brand_mpn_to_ids),
    )


def _resolve_master_patch_from_index(
    ix: _MasterPatchIndex,
    *,
    ean: str | None,
    mpn_norm: str,
    brand_norm: str,
    asin: str | None,
) -> tuple[int | None, str | None]:
    """Same contract as the former SQL resolver: unique id or ``not_found`` / ``ambiguous``."""
    hits: list[int] = []

    if ean:
        e = str(ean).strip()
        if e:
            lst = ix.ean_to_ids.get(e, [])
            if len(lst) > 1:
                return None, "ambiguous"
            if len(lst) == 1:
                hits.append(int(lst[0]))

    if mpn_norm:
        lm = mpn_norm.strip().lower()
        if brand_norm:
            lb = brand_norm.strip().lower()
            lst = ix.mpn_brand_to_ids.get((lm, lb), [])
        else:
            lst = ix.mpn_to_ids.get(lm, [])
        if len(lst) > 1:
            return None, "ambiguous"
        if len(lst) == 1:
            hits.append(int(lst[0]))

    if asin:
        a = str(asin).strip().upper()
        if a:
            lst = ix.asin_to_ids.get(a, [])
            if len(lst) > 1:
                return None, "ambiguous"
            if len(lst) == 1:
                hits.append(int(lst[0]))

    if not hits:
        return None, "not_found"
    u = {*hits}
    if len(u) != 1:
        return None, "ambiguous"
    return u.pop(), None


def _mpn_brand_pair_conflicts_from_index(
    ix: _MasterPatchIndex,
    row_id: int,
    mpn: str,
    brand: str,
) -> bool:
    """Another master row already uses this trimmed **(mpn, brand)** identity (snapshot), excluding ``row_id``."""
    lm = str(mpn).strip().lower()
    lb = str(brand).strip().lower()
    if not lb or not lm:
        return False
    lst = ix.brand_mpn_to_ids.get((lb, lm), [])
    return any(i != row_id for i in lst)


def _parse_master_row_id(value: Any) -> int | None:
    """Strict positive integer from Excel/CSV (handles ``12345.0``)."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if value <= 0 or value != int(value):
            return None
        return int(value)
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none"}:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    if f <= 0 or f > 9_007_199_254_740_992:  # loose guard against float garbage
        return None
    i = int(f)
    if abs(f - i) > 1e-9:
        return None
    return i if i > 0 else None


def _normalize_sheet_category(value: Any) -> str | None:
    if value is None:
        return None
    oc = str(value).strip()
    if not oc or oc.lower() == "nan":
        return None
    ncat_raw = _master_cleanup_strip_text(oc)
    return ncat_raw if ncat_raw else None


def _ean_compare_str(db_val: Any, new_ean: str) -> bool:
    """True if ``new_ean`` should replace ``db_val`` (already stripped)."""
    ds = str(db_val).strip() if db_val is not None else ""
    return ds != new_ean


def _asin_compare_norm(db_val: Any, new_asin: str | None) -> bool:
    if new_asin is None:
        return False
    d = _norm_asin(db_val)
    return (d or "") != (new_asin or "")


def _amazon_url_compare_norm(db_val: Any, new_url: Any) -> bool:
    d = _norm_amazon_url(db_val)
    n = _norm_amazon_url(new_url)
    return (d or "") != (n or "")


def _amazon_sales_compare(db_val: Any, new_val: int) -> bool:
    if db_val is None:
        return True
    try:
        return int(db_val) != int(new_val)
    except (TypeError, ValueError):
        return True


def _title_compare_normalized(db_mpn: str, db_brand: str, db_title: Any, t_new: str) -> bool:
    _, _, t_db, _ = normalize_master_row_texts(
        db_mpn or "—",
        db_brand or "—",
        str(db_title if db_title is not None else "").strip(),
        None,
    )
    return t_new != t_db


def _category_compare_norm(db_val: Any, cat_new: str) -> bool:
    d = _normalize_sheet_category(db_val)
    return (d or "") != (cat_new or "")


def ingest_master_identifier_patches(
    session: Session,
    items: Sequence[Mapping[str, Any]],
    *,
    chunk_size: int = 200,
    insert_batch_size: int = 1,
    on_progress: Callable[[float, str], None] | None = None,
    update_ean: bool = True,
    update_asin: bool = True,
    update_amazon_monthly_sales: bool = True,
    update_mpn: bool = False,
    update_title: bool = False,
    update_category: bool = False,
    update_brand: bool = False,
    fill_missing_only: bool = True,
) -> dict[str, int]:
    """
    Update existing ``master_products`` rows. Match either:

    * **``master_id``** — primary key from an exported master sheet (preferred when you edited the export); or
    * **EAN / MPN** (+ optional brand) / **ASIN** — same resolution as before when ``master_id`` is absent.

    Optional sheet keys: ``ean``, ``mpn_norm``, ``brand_match``, ``asin``, ``amazon_url``, ``amazon_monthly_sales``,
    ``sheet_title``, ``sheet_category``, ``sheet_brand`` (latter three when columns were mapped).

    When ``fill_missing_only`` is true (default), only fills blank DB fields (per ``update_*`` flags). Syncs ``products``
    for touched master ids.

    Rows are **skipped** when every selected column already matches the database (no redundant ``UPDATE``).
    """
    if insert_batch_size < 1:
        raise ValueError("insert_batch_size must be >= 1")

    n_items = len(items)
    updated_master = 0
    skipped = 0
    not_found = 0
    ambiguous = 0
    mpn_update_skipped = 0
    brand_update_skipped = 0
    touched_ids: list[int] = []
    updates_since_commit = 0

    session.commit()

    if on_progress is not None:
        on_progress(0.02, "Loading `master_products` into memory for fast matching…")
    ix = _load_master_patch_index(session)
    session.commit()
    if on_progress is not None:
        on_progress(
            0.06,
            f"Indexed **{len(ix.by_id):,}** master row(s). Applying **{n_items:,}** patch line(s)…",
        )

    def _want_fill(db_val: Any, sheet_val: Any) -> bool:
        if sheet_val is None or str(sheet_val).strip() == "":
            return False
        if not fill_missing_only:
            return True
        return _db_str_blank(db_val)

    def _want_fill_ams(_db_ams: Any, sheet_ams: Any) -> bool:
        if sheet_ams is None:
            return False
        if not fill_missing_only:
            return True
        return _db_ams is None

    _progress_every = 1000
    for idx, raw in enumerate(items):
        if on_progress is not None and n_items > 0 and (idx % _progress_every == 0 or idx == n_items - 1):
            frac = idx / max(1, n_items - 1) if n_items > 1 else 1.0
            on_progress(0.06 + 0.78 * frac, f"Identifier patches {idx + 1:,}/{n_items:,}…")

        ean_v = raw.get("ean")
        ean: str | None = None if ean_v is None or ean_v == "" else str(ean_v).strip() or None
        mpn_norm = str(raw.get("mpn_norm") or "").strip()
        brand_norm = str(raw.get("brand_match") or "").strip()
        asin = _norm_asin(raw.get("asin"))
        amazon_url = _norm_amazon_url(raw.get("amazon_url"))
        if asin is None and amazon_url is not None:
            asin = _asin_from_amazon_url(amazon_url)
        amazon_monthly_sales = _parse_amazon_monthly_sales(raw.get("amazon_monthly_sales"))

        mid: int | None = None
        err: str | None = None
        master_id_parsed = _parse_master_row_id(raw.get("master_id"))
        if master_id_parsed is not None:
            if master_id_parsed not in ix.by_id:
                not_found += 1
                continue
            mid = master_id_parsed
        else:
            mid, err = _resolve_master_patch_from_index(
                ix,
                ean=ean,
                mpn_norm=mpn_norm,
                brand_norm=brand_norm,
                asin=asin,
            )
            if mid is None:
                if err == "ambiguous":
                    ambiguous += 1
                else:
                    not_found += 1
                continue

        cur_row = ix.by_id.get(mid)
        if not cur_row:
            not_found += 1
            continue
        db_mpn = cur_row["mpn"]
        db_brand = cur_row["brand"]
        db_title = cur_row.get("title")
        db_category = cur_row.get("category")
        db_ean = cur_row["ean"]
        db_asin = cur_row["asin"]
        db_url = cur_row["amazon_url"]
        db_ams = cur_row["amazon_monthly_sales"]

        db_mpn_s = str(db_mpn).strip() if db_mpn is not None else ""
        db_brand_s = str(db_brand).strip() if db_brand is not None else ""

        set_parts: list[str] = []
        params: dict[str, Any] = {"id": mid}
        products_ops: list[tuple[Any, dict[str, Any]]] = []

        if update_ean and ean is not None and _want_fill(db_ean, ean) and _ean_compare_str(db_ean, ean):
            set_parts.append("ean = :ean")
            params["ean"] = ean
        if update_asin:
            if asin is not None and _want_fill(db_asin, asin) and _asin_compare_norm(db_asin, asin):
                set_parts.append("asin = :asin")
                params["asin"] = asin
            if amazon_url is not None and _want_fill(db_url, amazon_url) and _amazon_url_compare_norm(db_url, amazon_url):
                set_parts.append("amazon_url = :amazon_url")
                params["amazon_url"] = amazon_url
        if (
            update_amazon_monthly_sales
            and amazon_monthly_sales is not None
            and _want_fill_ams(db_ams, amazon_monthly_sales)
            and _amazon_sales_compare(db_ams, int(amazon_monthly_sales))
        ):
            set_parts.append("amazon_monthly_sales = :ams")
            params["ams"] = int(amazon_monthly_sales)

        sheet_title = raw.get("sheet_title")
        if (
            update_title
            and sheet_title is not None
            and str(sheet_title).strip() != ""
            and str(sheet_title).strip().lower() != "nan"
        ):
            _, _, t_new, _ = normalize_master_row_texts(
                db_mpn_s or "—",
                db_brand_s or "—",
                str(sheet_title).strip(),
                None,
            )
            if (
                t_new
                and _want_fill(db_title, t_new)
                and _title_compare_normalized(db_mpn_s, db_brand_s, db_title, t_new)
            ):
                set_parts.append("title = :title")
                params["title"] = t_new

        sheet_cat = raw.get("sheet_category")
        if (
            update_category
            and sheet_cat is not None
            and str(sheet_cat).strip() != ""
            and str(sheet_cat).strip().lower() != "nan"
        ):
            cat_new = _normalize_sheet_category(sheet_cat)
            if (
                cat_new is not None
                and _want_fill(db_category, cat_new)
                and _category_compare_norm(db_category, cat_new)
            ):
                set_parts.append("category = :category")
                params["category"] = cat_new

        sheet_brand_raw = raw.get("sheet_brand")
        brand_sheet_final = ""
        if (
            update_brand
            and sheet_brand_raw is not None
            and str(sheet_brand_raw).strip() != ""
            and str(sheet_brand_raw).strip().lower() != "nan"
        ):
            _, brand_sheet_final, _, _ = normalize_master_row_texts(
                db_mpn_s or "—",
                str(sheet_brand_raw).strip(),
                "Product",
                None,
            )

        mpn_changing = (
            update_mpn
            and bool(mpn_norm)
            and _want_fill(db_mpn, mpn_norm)
            and mpn_norm != db_mpn_s
        )
        brand_changing = (
            update_brand
            and bool(brand_sheet_final)
            and _want_fill(db_brand, brand_sheet_final)
            and brand_sheet_final.strip().lower() != db_brand_s.lower()
        )

        if mpn_changing or brand_changing:
            new_m = mpn_norm if mpn_changing else db_mpn_s
            new_b = brand_sheet_final if brand_changing else db_brand_s
            old_mpn = db_mpn_s
            old_brand = db_brand_s
            if _mpn_brand_pair_conflicts_from_index(ix, mid, new_m, new_b):
                if mpn_changing:
                    mpn_update_skipped += 1
                if brand_changing:
                    brand_update_skipped += 1
            elif _products_catalog_identity_taken_elsewhere(
                session,
                new_mpn=new_m,
                new_brand=new_b,
                old_mpn=old_mpn,
                old_brand=old_brand,
            ):
                if mpn_changing:
                    mpn_update_skipped += 1
                if brand_changing:
                    brand_update_skipped += 1
            else:
                if mpn_changing and brand_changing:
                    products_ops.append(
                        (
                            text(
                                "UPDATE products SET mpn = :new_mpn, brand = :new_brand WHERE "
                                "LOWER(TRIM(mpn)) = LOWER(TRIM(:old_mpn)) AND "
                                "LOWER(TRIM(brand)) = LOWER(TRIM(:old_brand))",
                            ),
                            {
                                "new_mpn": new_m,
                                "new_brand": new_b,
                                "old_mpn": old_mpn,
                                "old_brand": old_brand,
                            },
                        ),
                    )
                elif mpn_changing:
                    if old_mpn != new_m and old_brand:
                        products_ops.append(
                            (
                                text(
                                    "UPDATE products SET mpn = :new_mpn WHERE "
                                    "LOWER(TRIM(mpn)) = LOWER(TRIM(:old_mpn)) AND "
                                    "LOWER(TRIM(brand)) = LOWER(TRIM(:old_brand))",
                                ),
                                {
                                    "new_mpn": new_m,
                                    "old_mpn": old_mpn,
                                    "old_brand": old_brand,
                                },
                            ),
                        )
                elif brand_changing:
                    if old_mpn:
                        products_ops.append(
                            (
                                text(
                                    "UPDATE products SET brand = :new_brand WHERE "
                                    "LOWER(TRIM(mpn)) = LOWER(TRIM(:old_mpn)) AND "
                                    "LOWER(TRIM(brand)) = LOWER(TRIM(:old_brand))",
                                ),
                                {
                                    "new_brand": new_b,
                                    "old_mpn": old_mpn,
                                    "old_brand": old_brand,
                                },
                            ),
                        )
                if mpn_changing:
                    set_parts.append("mpn = :mpn")
                    params["mpn"] = new_m
                if brand_changing:
                    set_parts.append("brand = :brand")
                    params["brand"] = new_b

        if not set_parts:
            skipped += 1
            continue

        master_sql = text(f"UPDATE master_products SET {', '.join(set_parts)} WHERE id = :id")
        _patch_row_writes_retry(
            session,
            products_ops=products_ops,
            master_stmt=master_sql,
            master_params=params,
        )
        updated_master += 1
        touched_ids.append(mid)
        if "ean" in params:
            cur_row["ean"] = params["ean"]
        if "asin" in params:
            cur_row["asin"] = params["asin"]
        if "amazon_url" in params:
            cur_row["amazon_url"] = params["amazon_url"]
        if "ams" in params:
            cur_row["amazon_monthly_sales"] = params["ams"]
        if "mpn" in params:
            cur_row["mpn"] = params["mpn"]
        if "brand" in params:
            cur_row["brand"] = params["brand"]
        if "title" in params:
            cur_row["title"] = params["title"]
        if "category" in params:
            cur_row["category"] = params["category"]

        updates_since_commit += 1
        if updates_since_commit >= insert_batch_size:
            session.commit()
            updates_since_commit = 0

    if updates_since_commit:
        session.commit()

    if on_progress is not None:
        on_progress(0.88, "Syncing catalog products…")

    sync_ids = sorted({int(i) for i in touched_ids if int(i) > 0})
    updated_products, inserted_products = _sync_catalog_from_master_ids(
        session,
        sync_ids,
        chunk_size=chunk_size,
        commit_each_chunk=True,
    )

    if on_progress is not None:
        on_progress(1.0, "Finishing…")

    return {
        "added": 0,
        "skipped": skipped,
        "updated_master": updated_master,
        "not_found": not_found,
        "ambiguous": ambiguous,
        "mpn_update_skipped": mpn_update_skipped,
        "brand_update_skipped": brand_update_skipped,
        "updated_products": updated_products,
        "inserted_products": inserted_products,
    }


def queue_master_incomplete_rows(session: Session, rows: Sequence[Mapping[str, Any]]) -> int:
    """Store rows missing required master fields for completion in the Master database UI."""
    if not rows:
        return 0
    for raw in rows:
        session.add(
            MasterIncompleteRow(
                mpn=_nullable_str(raw.get("mpn")),
                brand=_nullable_str(raw.get("brand")),
                title=_nullable_str(raw.get("title")),
                ean=_nullable_str(raw.get("ean")),
                category=_nullable_str(raw.get("category")),
                asin=_norm_asin(raw.get("asin")),
                amazon_monthly_sales=_parse_amazon_monthly_sales(raw.get("amazon_monthly_sales")),
                amazon_url=_norm_amazon_url(raw.get("amazon_url")),
            ),
        )
    session.flush()
    return len(rows)


def ingest_master_datasheet(
    session: Session,
    items: Sequence[Mapping[str, Any]],
    *,
    chunk_size: int = 200,
    insert_batch_size: int = 64,
    on_progress: Callable[[float, str], None] | None = None,
    update_existing_master: bool = False,
    update_ean: bool = True,
    update_asin: bool = True,
    update_amazon_monthly_sales: bool = True,
    update_mpn: bool = False,
) -> dict[str, int]:
    """
    Load into ``master_products``: insert new normalized MPN+Brand rows; optionally **update** fields
    on existing rows when the same case-insensitive MPN+Brand key is already present.

    ``mpn`` in ``items`` may be ``EAN:{gtin}`` when the sheet had EAN only.

    Uses one prefetch of existing keys + batched inserts. After each insert batch the session is
    **committed** so InnoDB does not hold locks for the full file (avoids lock wait timeout 1205).

    Syncs ``products`` for master rows **inserted or updated** in this run, committing after each
    sync chunk when ``chunk_size`` batching applies.

    The caller may still ``commit`` at the end; it is a no-op if everything was already committed.

    ``items`` values: ``mpn`` (manufacturer part or ``EAN:{gtin}``), ``brand``, ``title`` (required strings); optional ``ean``, ``category``,
    ``asin``, ``amazon_monthly_sales``, ``amazon_url``.

    When ``update_existing_master`` is true, sub-flags select which columns to overwrite from the sheet
    (non-empty sheet values only). **MPN** updates skip if another master row already owns the target
    MPN+Brand pair; when MPN text changes, matching ``products`` rows get the new MPN so catalog sync still joins.
    """
    if insert_batch_size < 1:
        raise ValueError("insert_batch_size must be >= 1")

    n_items = len(items)
    if on_progress is not None:
        on_progress(0.0, "Loading existing master keys…")

    key_to_id = _load_master_key_to_id(session)
    master_keys = set(key_to_id)
    if on_progress is not None:
        on_progress(0.04, f"Loaded {len(master_keys):,} key(s). Processing rows…")
    session.commit()

    added = 0
    skipped = 0
    updated_master = 0
    mpn_update_skipped = 0
    new_ids: list[int] = []
    touched_ids: list[int] = []
    pending: list[MasterProduct] = []

    def _flush_pending() -> None:
        nonlocal pending, added
        if not pending:
            return
        session.add_all(pending)
        session.flush()
        for row in pending:
            rid = int(row.id)
            new_ids.append(rid)
            touched_ids.append(rid)
            key_to_id[_master_row_identity(str(row.mpn), str(row.brand))] = rid
        added += len(pending)
        pending = []
        session.commit()

    updates_since_commit = 0

    for idx, raw in enumerate(items):
        if on_progress is not None and n_items > 0 and idx % 2000 == 0:
            frac = idx / n_items
            on_progress(0.05 + 0.80 * frac, f"Master ingest {idx:,}/{n_items:,}…")

        mpn_raw = str(raw.get("mpn", "")).strip()
        brand_raw = str(raw.get("brand", "")).strip()
        title_raw = str(raw.get("title", "")).strip()
        cat_v = raw.get("category")
        category_src: str | None
        if cat_v is None or cat_v == "":
            category_src = None
        else:
            category_src = str(cat_v).strip() or None

        mpn, brand, title, category = normalize_master_row_texts(
            mpn_raw,
            brand_raw,
            title_raw,
            category_src,
        )
        if not mpn or not brand or not title:
            continue
        ean_v = raw.get("ean")
        ean: str | None = None if ean_v is None or ean_v == "" else str(ean_v).strip() or None

        asin = _norm_asin(raw.get("asin"))
        amazon_url = _norm_amazon_url(raw.get("amazon_url"))
        if asin is None and amazon_url is not None:
            asin = _asin_from_amazon_url(amazon_url)
        amazon_monthly_sales = _parse_amazon_monthly_sales(raw.get("amazon_monthly_sales"))

        key = _master_row_identity(mpn, brand)
        if key in master_keys:
            if not update_existing_master:
                skipped += 1
                continue

            mid = key_to_id.get(key)
            if mid is None:
                skipped += 1
                continue

            set_parts: list[str] = []
            params: dict[str, Any] = {"id": mid}

            if update_ean and ean is not None:
                set_parts.append("ean = :ean")
                params["ean"] = ean
            if update_asin:
                if asin is not None:
                    set_parts.append("asin = :asin")
                    params["asin"] = asin
                if amazon_url is not None:
                    set_parts.append("amazon_url = :amazon_url")
                    params["amazon_url"] = amazon_url
            if update_amazon_monthly_sales and amazon_monthly_sales is not None:
                set_parts.append("amazon_monthly_sales = :ams")
                params["ams"] = int(amazon_monthly_sales)

            if update_mpn:
                prev = session.execute(
                    text("SELECT mpn, brand FROM master_products WHERE id = :id"),
                    {"id": mid},
                ).first()
                old_mpn = str(prev[0]) if prev and prev[0] is not None else mpn
                old_brand = str(prev[1]) if prev and prev[1] is not None else brand
                if _master_mpn_update_conflicts(session, mid, brand, mpn):
                    mpn_update_skipped += 1
                else:
                    if old_mpn != mpn:
                        session.execute(
                            text(
                                "UPDATE products SET mpn = :new_mpn WHERE "
                                "LOWER(TRIM(mpn)) = LOWER(TRIM(:old_mpn)) AND "
                                "LOWER(TRIM(brand)) = LOWER(TRIM(:old_brand))",
                            ),
                            {"new_mpn": mpn, "old_mpn": old_mpn, "old_brand": old_brand},
                        )
                    set_parts.append("mpn = :mpn")
                    params["mpn"] = mpn

            if not set_parts:
                skipped += 1
                continue

            session.execute(
                text(f"UPDATE master_products SET {', '.join(set_parts)} WHERE id = :id"),
                params,
            )
            updated_master += 1
            touched_ids.append(mid)
            updates_since_commit += 1
            if updates_since_commit >= insert_batch_size:
                session.commit()
                updates_since_commit = 0
            continue

        master_keys.add(key)
        pending.append(
            MasterProduct(
                mpn=mpn,
                brand=brand,
                title=title,
                ean=ean,
                category=category,
                asin=asin,
                amazon_monthly_sales=amazon_monthly_sales,
                amazon_url=amazon_url,
            ),
        )
        if len(pending) >= insert_batch_size:
            _flush_pending()

    _flush_pending()

    if updates_since_commit:
        session.commit()

    if on_progress is not None:
        on_progress(0.88, "Syncing catalog products…")

    sync_ids = sorted({int(i) for i in (*new_ids, *touched_ids) if int(i) > 0})
    updated_products, inserted_products = _sync_catalog_from_master_ids(
        session,
        sync_ids,
        chunk_size=chunk_size,
        commit_each_chunk=True,
    )
    if on_progress is not None:
        on_progress(1.0, "Finishing…")

    return {
        "added": added,
        "skipped": skipped,
        "updated_master": updated_master,
        "mpn_update_skipped": mpn_update_skipped,
        "updated_products": updated_products,
        "inserted_products": inserted_products,
    }


class ProductMatcher:
    """Bulk-match vendor lines to products and merge vendor offers (insert or update when needed)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ingest_vendor_catalog(
        self,
        vendor_name: str,
        items: Sequence[VendorProductInput | Mapping[str, Any]],
        *,
        chunk_size: int = 500,
    ) -> int:
        """
        For each vendor line: resolve ``product_id`` by (mpn, brand); create ``Product``
        rows when missing; insert or update ``vendor_offers``. Does not commit the session.

        Existing offers for the same vendor + product + region are **left unchanged** unless
        **price** (GBP/EUR/USD) or **stock_level** differs from the feed (to 4 dp for money).

        If env ``VENDOR_OFFERS_SNAPSHOT`` is truthy, removes ``vendor_offers`` for this vendor
        whose (``product_id``, ``region``) is not in the current feed so dropped lines leave
        the catalog.

        Returns the number of offer rows **inserted or updated** (unchanged rows are skipped).
        """
        vname = vendor_name.strip()
        if not vname:
            raise ValueError("vendor_name must be non-empty")

        prepared = _prepare_items(items)
        if not prepared:
            return 0

        keys = [(p.mpn, p.brand) for p in prepared]
        product_ids_by_key = self._load_existing_product_ids(keys, chunk_size=chunk_size)

        to_create = [p for p in prepared if _identity_key(p.mpn, p.brand) not in product_ids_by_key]
        if to_create:
            self._bulk_insert_products(to_create)
            self._session.flush()
            created_map = self._load_existing_product_ids(
                [(p.mpn, p.brand) for p in to_create],
                chunk_size=chunk_size,
            )
            product_ids_by_key.update(created_map)

        id_keys = [_identity_key(p.mpn, p.brand) for p in prepared]
        if any(k not in product_ids_by_key for k in id_keys):
            product_ids_by_key.update(
                self._load_existing_product_ids(keys, chunk_size=chunk_size),
            )

        if _env_truthy("VENDOR_OFFERS_SNAPSHOT"):
            keep_keys: set[tuple[int, str]] = set()
            for p in prepared:
                pid = product_ids_by_key[_identity_key(p.mpn, p.brand)]
                keep_keys.add((pid, str(p.region).strip().upper()))
            n_pr = self._prune_vendor_offers_outside_keys(vname, keep_keys, chunk_size=chunk_size)
            if n_pr:
                print(
                    f"VENDOR_OFFERS_SNAPSHOT: removed {n_pr} offer row(s) not in current feed for vendor {vname!r}",
                    file=sys.stderr,
                    flush=True,
                )

        unique_pids = sorted({product_ids_by_key[_identity_key(p.mpn, p.brand)] for p in prepared})
        offer_groups = self._load_vendor_offers_grouped(vname, unique_pids, chunk_size=chunk_size)
        stamp_fallback = datetime.now(timezone.utc)
        n_written = 0

        for p in prepared:
            pid = product_ids_by_key[_identity_key(p.mpn, p.brand)]
            reg = str(p.region).strip().upper()
            okey = (pid, reg)
            orows = list(offer_groups.get(okey, ()))

            for extra in orows[1:]:
                self._session.delete(extra)
            primary = orows[0] if orows else None

            lu = p.last_updated if p.last_updated is not None else stamp_fallback

            if primary is None:
                self._session.add(
                    VendorOffer(
                        product_id=pid,
                        vendor_name=vname,
                        region=reg,
                        price_gbp=p.price_gbp,
                        price_eur=p.price_eur,
                        price_usd=p.price_usd,
                        stock_level=p.stock_level,
                        last_updated=lu,
                    ),
                )
                n_written += 1
                continue

            if _vendor_offer_matches_prepared(primary, p):
                continue

            self._session.execute(
                update(VendorOffer)
                .where(VendorOffer.id == primary.id)
                .values(
                    price_gbp=p.price_gbp,
                    price_eur=p.price_eur,
                    price_usd=p.price_usd,
                    stock_level=p.stock_level,
                    last_updated=lu,
                ),
            )
            n_written += 1

        return n_written

    def _prune_vendor_offers_outside_keys(
        self,
        vendor_name: str,
        keep: set[tuple[int, str]],
        *,
        chunk_size: int,
    ) -> int:
        stmt = select(VendorOffer.id, VendorOffer.product_id, VendorOffer.region).where(
            VendorOffer.vendor_name == vendor_name,
        )
        rows = self._session.execute(stmt).all()
        to_del: list[int] = []
        for rid, pid, reg in rows:
            k = (int(pid), str(reg).strip().upper())
            if k not in keep:
                to_del.append(int(rid))
        n = 0
        for batch in _chunks(to_del, chunk_size):
            res = self._session.execute(delete(VendorOffer).where(VendorOffer.id.in_(batch)))
            n += int(res.rowcount or 0)
        return n

    def _load_vendor_offers_grouped(
        self,
        vendor_name: str,
        product_ids: Sequence[int],
        *,
        chunk_size: int,
    ) -> dict[tuple[int, str], list[VendorOffer]]:
        out: dict[tuple[int, str], list[VendorOffer]] = defaultdict(list)
        ids = list(dict.fromkeys(int(i) for i in product_ids))
        for batch in _chunks(ids, chunk_size):
            stmt = (
                select(VendorOffer)
                .where(
                    VendorOffer.vendor_name == vendor_name,
                    VendorOffer.product_id.in_(batch),
                )
                .order_by(VendorOffer.id)
            )
            for offer in self._session.scalars(stmt):
                k = (int(offer.product_id), str(offer.region).strip().upper())
                out[k].append(offer)
        return out

    def _load_existing_product_ids(
        self,
        keys: list[tuple[str, str]],
        *,
        chunk_size: int,
    ) -> dict[tuple[str, str], int]:
        out: dict[tuple[str, str], int] = {}
        col_mpn = Product.__table__.c.mpn
        col_brand = Product.__table__.c.brand
        for batch in _chunks(list(dict.fromkeys(keys)), chunk_size):
            stmt = select(Product.id, col_mpn, col_brand).where(
                tuple_(col_mpn, col_brand).in_(batch),
            )
            for row in self._session.execute(stmt).all():
                k = _identity_key(str(row.mpn), str(row.brand))
                out[k] = int(row.id)
        return out

    def _bulk_insert_products(self, rows: list[_PreparedItem]) -> None:
        """Insert products; on duplicate (mpn, brand) refresh title, category, ean from the feed."""
        if not rows:
            return
        mappings = [
            {
                "mpn": p.mpn,
                "brand": p.brand,
                "title": p.title,
                "category": p.category,
                "ean": p.ean,
            }
            for p in rows
        ]
        stmt = mysql_insert(Product).values(mappings)
        stmt = stmt.on_duplicate_key_update(
            title=stmt.inserted.title,
            category=stmt.inserted.category,
            ean=stmt.inserted.ean,
        )
        self._session.execute(stmt)
