"""Streamlit admin dashboard: map columns, ingest CSV/TSV/text/Excel via ProductMatcher."""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import Base, MasterIncompleteRow, get_engine
from feeds.db_sources import list_enabled_feed_sources
from core.matcher import (
    ProductMatcher,
    _asin_from_amazon_url,
    _norm_amazon_url,
    _norm_asin,
    _parse_amazon_monthly_sales,
    _parse_master_row_id,
    ingest_master_datasheet,
    ingest_master_identifier_patches,
    normalize_master_row_texts,
    queue_master_incomplete_rows,
    soft_strip_master_field,
)

st.set_page_config(page_title="B2B catalog — admin", layout="wide")

STANDARD_FIELDS = ("MPN", "EAN", "Title", "Brand", "Category", "Stock", "Price")
MASTER_FIELDS = (
    "Master row ID",
    "MPN",
    "Brand",
    "Title",
    "EAN",
    "Category",
    "ASIN",
    "Monthly sale on Amazon",
    "Amazon URL",
)
REQUIRED_VENDOR = {"MPN", "Brand", "Price"}
REQUIRED_MASTER = {"Brand", "Title"}
CHUNK_ROWS = 350
INGEST_VENDOR_LABEL = "Vendor catalog (prices & stock)"
INGEST_MASTER_LABEL = "Master datasheet (titles, EAN, category — no prices)"
_NONE = "(not mapped)"

_LEADING_CURRENCY = re.compile(r"^\s*\$?\s*")


def _delimiter_for_text_file(filename_lower: str, first_line: str) -> str:
    """Pick a field separator for delimiter-separated text (CSV/TSV/TXT)."""
    if filename_lower.endswith(".tsv"):
        return "\t"
    if filename_lower.endswith(".txt"):
        tabs = first_line.count("\t")
        semi = first_line.count(";")
        comma = first_line.count(",")
        if tabs > 0 and tabs >= semi and tabs >= comma:
            return "\t"
        if semi > comma:
            return ";"
        return ","
    if first_line.count(";") > first_line.count(","):
        return ";"
    return ","


def _decode_text_file_bytes(raw: bytes) -> str:
    """Decode CSV/TSV bytes (UTF-8, Excel Windows-1252, or ISO Latin). Latin-1 never fails per-byte."""
    if raw.startswith(b"\xef\xbb\xbf"):
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raw = raw[3:]
    for encoding in ("utf-8", "cp1252", "iso-8859-15"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def _read_text_table(raw: bytes, sep: str) -> pd.DataFrame:
    text = _decode_text_file_bytes(raw)
    bio = io.StringIO(text)
    kw: dict[str, Any] = dict(
        sep=sep,
        quotechar="\"",
        engine="python",
        dtype=str,
        na_filter=False,
    )
    try:
        return pd.read_csv(bio, on_bad_lines="skip", **kw)
    except TypeError:
        bio.seek(0)
        return pd.read_csv(bio, **kw)


def _read_uploaded_df(data: bytes, filename: str) -> pd.DataFrame:
    name = filename.lower()
    bio = io.BytesIO(data)
    if name.endswith((".xlsx", ".xlsm")):
        # Read as strings so identifiers (especially EAN) keep leading zeros when Excel stores them as text.
        try:
            return pd.read_excel(bio, engine="openpyxl", dtype=str)
        except Exception:
            bio.seek(0)
            return pd.read_excel(bio, engine="openpyxl")
    raw = data
    snippet = raw[:8192]
    first_line = snippet.decode("latin-1", errors="replace").splitlines()[0] if snippet else ""
    sep = _delimiter_for_text_file(name, first_line)
    return _read_text_table(raw, sep)


def _cell_str(row: pd.Series, col: str | None) -> str:
    if col is None or col not in row.index:
        return ""
    v = row[col]
    if pd.isna(v):
        return ""
    return str(v).strip()


def _clean_price(v: Any) -> Decimal | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return Decimal(str(v))
    s = str(v).strip()
    if not s:
        return None
    s = _LEADING_CURRENCY.sub("", s).replace(",", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _clean_stock(v: Any) -> int | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (np.integer, int)) and not isinstance(v, bool):
        return int(v)
    if isinstance(v, (np.floating, float)):
        if np.isnan(v):
            return None
        return int(round(float(v)))
    try:
        s = str(v).strip()
        if not s:
            return None
        return int(round(float(s)))
    except ValueError:
        return None


def _effective_master_mpn(mpn: str, ean: str | None) -> str:
    """``master_products.mpn``: real MPN when present, else ``EAN:{gtin}`` when EAN is set."""
    m = (mpn or "").strip()
    if m:
        return m
    if ean is None:
        return ""
    e = str(ean).strip()
    if not e:
        return ""
    return f"EAN:{e}"


def _ean_from_value(v: Any) -> str | None:
    """Normalize EAN/GTIN as a string. Leading zeros are kept only if the cell is already text-like."""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() == "nan":
            return None
        if re.fullmatch(r"-?\d+\.0+", s):
            s = s.split(".", 1)[0]
        return s
    if isinstance(v, (np.integer, int)) and not isinstance(v, bool):
        return str(int(v))
    if isinstance(v, (np.floating, float)):
        if np.isnan(v):
            return None
        f = float(v)
        if f.is_integer():
            return str(int(f))
        s = str(v).strip()
        return s or None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    if re.fullmatch(r"-?\d+\.0+", s):
        s = s.split(".", 1)[0]
    return s


def _apply_price_for_region(out: dict[str, Any], region: str, price: Decimal) -> None:
    """Map the uploaded ``Price`` column to the correct currency column and offer ``region``."""
    if region == "UK":
        out["price_gbp"] = price
        out["region"] = "UK"
    elif region == "EU":
        out["price_eur"] = price
        out["region"] = "EU"
    elif region == "USA":
        out["price_usd"] = price
        out["region"] = "USA"
    else:
        raise ValueError(f"Unsupported region: {region!r}")


def _build_row_dict(
    row: pd.Series,
    mapping: dict[str, str | None],
    region: str,
) -> dict[str, Any] | None:
    mpn_col = mapping["MPN"]
    brand_col = mapping["Brand"]
    price_col = mapping["Price"]
    mpn = _cell_str(row, mpn_col)
    brand = _cell_str(row, brand_col)
    price = _clean_price(row[price_col]) if price_col else None
    if not mpn or not brand or price is None or price <= 0:
        return None

    title_col = mapping["Title"]
    title = _cell_str(row, title_col) or mpn
    ean_col = mapping["EAN"]
    ean: str | None = None
    if ean_col and ean_col in row.index:
        ean = _ean_from_value(row[ean_col])
    cat_col = mapping["Category"]
    cat = _cell_str(row, cat_col) or None
    stock_col = mapping["Stock"]
    stock: int | None = None
    if stock_col and stock_col in row.index:
        stock = _clean_stock(row[stock_col])

    out: dict[str, Any] = {
        "mpn": mpn,
        "brand": brand,
        "title": title,
        "ean": ean,
        "category": cat,
        "stock_level": stock,
    }
    _apply_price_for_region(out, region, price)
    return out


def _collect_master_rows_from_df(
    df: pd.DataFrame,
    mapping: dict[str, str | None],
    bar: Any,
    *,
    parse_lo: float = 0.02,
    parse_hi: float = 0.14,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split into complete rows (ingest to master) and incomplete rows (queue for Master DB tab)."""
    mpn_c = mapping["MPN"]
    brand_c = mapping["Brand"]
    title_c = mapping["Title"]
    ean_c = mapping.get("EAN")
    cat_c = mapping.get("Category")
    asin_c = mapping.get("ASIN")
    amz_sales_c = mapping.get("Monthly sale on Amazon")
    amz_url_c = mapping.get("Amazon URL")

    n = len(df)
    if mpn_c and mpn_c in df.columns:
        mpn = df[mpn_c].fillna("").astype(str).str.strip()
    else:
        mpn = pd.Series("", index=df.index, dtype=str)
    brand = df[brand_c].fillna("").astype(str).str.strip()
    tit = df[title_c].fillna("").astype(str).str.strip()

    has_ean = ean_c is not None and ean_c in df.columns
    has_cat = cat_c is not None and cat_c in df.columns
    has_asin = asin_c is not None and asin_c in df.columns
    has_amz_sales = amz_sales_c is not None and amz_sales_c in df.columns
    has_amz_url = amz_url_c is not None and amz_url_c in df.columns
    ean_series = df[ean_c] if has_ean else None
    ean_present = np.zeros(n, dtype=bool)
    if has_ean and ean_series is not None:
        for i in range(n):
            if _ean_from_value(ean_series.iloc[i]) is not None:
                ean_present[i] = True
    blank = (mpn.to_numpy() == "") & (brand.to_numpy() == "") & ~ean_present
    cat_series = df[cat_c] if has_cat else None
    asin_series = df[asin_c] if has_asin else None
    amz_sales_series = df[amz_sales_c] if has_amz_sales else None
    amz_url_series = df[amz_url_c] if has_amz_url else None

    bar.progress(parse_lo, text=f"Parsing {n:,} row(s)…")
    time.sleep(0.02)

    rows_out: list[dict[str, Any]] = []
    incomplete_out: list[dict[str, Any]] = []
    data_positions = np.flatnonzero(~np.asarray(blank, dtype=bool))
    total_d = len(data_positions)
    for step, pos in enumerate(data_positions):
        if step % 5000 == 0 and total_d > 0:
            frac = step / total_d
            bar.progress(
                parse_lo + frac * (parse_hi - parse_lo),
                text=f"Parsing rows {step:,}/{total_d:,}…",
            )
            time.sleep(0.001)

        mp = str(mpn.iloc[pos])
        br = str(brand.iloc[pos])
        tr = str(tit.iloc[pos])

        ean_val = _ean_from_value(ean_series.iloc[pos]) if has_ean and ean_series is not None else None
        cat_val: str | None = None
        if has_cat and cat_series is not None:
            cv = cat_series.iloc[pos]
            if pd.notna(cv):
                s = str(cv).strip()
                cat_val = s if s else None

        def _opt_amazon() -> dict[str, Any]:
            o: dict[str, Any] = {}
            if has_asin and asin_series is not None:
                o["asin"] = _norm_asin(asin_series.iloc[pos])
            if has_amz_sales and amz_sales_series is not None:
                o["amazon_monthly_sales"] = _parse_amazon_monthly_sales(amz_sales_series.iloc[pos])
            if has_amz_url and amz_url_series is not None:
                o["amazon_url"] = _norm_amazon_url(amz_url_series.iloc[pos])
            return o

        has_id = bool(mp) or (ean_val is not None and str(ean_val).strip() != "")
        if br.strip() == "" or not has_id or tr.strip() == "":
            incomplete_out.append(
                {
                    "mpn": soft_strip_master_field(mp) if mp else None,
                    "brand": soft_strip_master_field(br) if br else None,
                    "title": soft_strip_master_field(tr) if tr else None,
                    "ean": ean_val,
                    "category": soft_strip_master_field(cat_val) if cat_val else None,
                    **_opt_amazon(),
                },
            )
            continue

        eff_mpn = _effective_master_mpn(mp, ean_val)
        nm, nb, t, cat_n = normalize_master_row_texts(eff_mpn, br, tr, cat_val)
        if not nm or not nb or not t:
            incomplete_out.append(
                {
                    "mpn": soft_strip_master_field(mp) if mp else None,
                    "brand": soft_strip_master_field(br) if br else None,
                    "title": soft_strip_master_field(tr) if tr else None,
                    "ean": ean_val,
                    "category": soft_strip_master_field(cat_val) if cat_val else None,
                    **_opt_amazon(),
                },
            )
            continue

        row_dict: dict[str, Any] = {
            "mpn": nm,
            "brand": nb,
            "title": t,
            "ean": ean_val,
            "category": cat_n,
        }
        row_dict.update(_opt_amazon())
        rows_out.append(row_dict)

    bar.progress(parse_hi, text="Parse complete.")
    time.sleep(0.01)
    return rows_out, incomplete_out


def _collect_master_identifier_patches_from_df(
    df: pd.DataFrame,
    mapping: dict[str, str | None],
    bar: Any,
    *,
    parse_lo: float = 0.02,
    parse_hi: float = 0.14,
) -> list[dict[str, Any]]:
    """Rows for :func:`ingest_master_identifier_patches` (match by **Master row ID** and/or EAN / MPN / ASIN / URL)."""
    id_c = mapping.get("Master row ID")
    mpn_c = mapping.get("MPN")
    brand_c = mapping.get("Brand")
    title_c = mapping.get("Title")
    cat_c = mapping.get("Category")
    ean_c = mapping.get("EAN")
    asin_c = mapping.get("ASIN")
    amz_sales_c = mapping.get("Monthly sale on Amazon")
    amz_url_c = mapping.get("Amazon URL")

    n = len(df)
    has_id_col = id_c is not None and id_c in df.columns
    id_series = df[id_c] if has_id_col else None
    if mpn_c and mpn_c in df.columns:
        mpn_ser = df[mpn_c].fillna("").astype(str)
    else:
        mpn_ser = pd.Series("", index=df.index, dtype=str)
    if brand_c and brand_c in df.columns:
        brand_ser = df[brand_c].fillna("").astype(str)
    else:
        brand_ser = pd.Series("", index=df.index, dtype=str)
    has_title_col = title_c is not None and title_c in df.columns
    has_cat_col = cat_c is not None and cat_c in df.columns
    has_ean = ean_c is not None and ean_c in df.columns
    ean_series = df[ean_c] if has_ean else None
    has_asin = asin_c is not None and asin_c in df.columns
    asin_series = df[asin_c] if has_asin else None
    has_amz_sales = amz_sales_c is not None and amz_sales_c in df.columns
    amz_sales_series = df[amz_sales_c] if has_amz_sales else None
    has_amz_url = amz_url_c is not None and amz_url_c in df.columns
    amz_url_series = df[amz_url_c] if has_amz_url else None

    bar.progress(parse_lo, text=f"Parsing identifier patch rows {n:,}…")
    time.sleep(0.02)

    out: list[dict[str, Any]] = []
    for pos in range(n):
        if pos % 5000 == 0 and n > 0:
            bar.progress(parse_lo + (pos / n) * (parse_hi - parse_lo), text=f"Parsing {pos:,}/{n:,}…")

        mp_raw = str(mpn_ser.iloc[pos]).strip()
        br_raw = str(brand_ser.iloc[pos]).strip()
        ean_val = _ean_from_value(ean_series.iloc[pos]) if has_ean and ean_series is not None else None

        mpn_norm = ""
        if mp_raw:
            mpn_norm, _, _, _ = normalize_master_row_texts(mp_raw, "—", "Product", None)
        brand_match = ""
        if br_raw:
            _, brand_match, _, _ = normalize_master_row_texts("—", br_raw, "Product", None)

        o: dict[str, Any] = {}
        if has_id_col and id_series is not None:
            mid = _parse_master_row_id(id_series.iloc[pos])
            if mid is not None:
                o["master_id"] = mid
        if ean_val is not None:
            o["ean"] = ean_val
        if mpn_norm:
            o["mpn_norm"] = mpn_norm
        if brand_match:
            o["brand_match"] = brand_match
        if has_title_col:
            tv = df[title_c].iloc[pos]
            o["sheet_title"] = "" if pd.isna(tv) else str(tv)
        if has_cat_col:
            cv = df[cat_c].iloc[pos]
            o["sheet_category"] = "" if pd.isna(cv) else str(cv)
        if brand_c and brand_c in df.columns and str(brand_ser.iloc[pos]).strip():
            o["sheet_brand"] = str(brand_ser.iloc[pos]).strip()
        if has_asin and asin_series is not None:
            o["asin"] = _norm_asin(asin_series.iloc[pos])
        if has_amz_sales and amz_sales_series is not None:
            o["amazon_monthly_sales"] = _parse_amazon_monthly_sales(amz_sales_series.iloc[pos])
        if has_amz_url and amz_url_series is not None:
            o["amazon_url"] = _norm_amazon_url(amz_url_series.iloc[pos])

        has_lookup = (
            o.get("master_id") is not None
            or bool(o.get("ean"))
            or bool(o.get("mpn_norm"))
            or bool(o.get("asin"))
        )
        if not has_lookup and o.get("amazon_url"):
            asin_guess = _asin_from_amazon_url(str(o["amazon_url"]))
            if asin_guess:
                o["asin"] = asin_guess
                has_lookup = True

        if not has_lookup:
            continue

        out.append(o)

    bar.progress(parse_hi, text="Parse complete.")
    time.sleep(0.01)
    return out


def _sidebar_run_feeds() -> None:
    """Run ``run_feeds.py`` on the local machine (cron-style automation) from the project root."""
    st.sidebar.divider()
    st.sidebar.subheader("Automated feeds")
    st.sidebar.caption(
        "Runs **`run_feeds.py`** on **this computer** (project folder, same `.env` as this app). "
        "Equivalent to a terminal in the repo. **From DB** uses enabled rows in **`supplier_feed_sources`** (FMS → Feed sources)."
    )
    use_from_db = st.sidebar.checkbox(
        "From database (`--from-db`)",
        value=True,
        key="admin_feeds_from_db",
        help="Loads enabled `supplier_feed_sources` from MySQL. Uncheck to use a JSON file instead.",
    )
    feed_id_extra: list[str] = []
    if use_from_db:
        try:
            _fe_rows = list_enabled_feed_sources(get_engine())
        except Exception:
            _fe_rows = []
        if _fe_rows:
            _labels: list[str] = []
            _id_by_label: dict[str, int] = {}
            for _r in _fe_rows:
                _vn = str(_r.get("vendor_name") or "").strip() or "—"
                _pr = str(_r.get("protocol") or "").strip() or "?"
                _fid = int(_r["id"])
                _lb = f"{_vn} — {_pr} (id {_fid})"
                _labels.append(_lb)
                _id_by_label[_lb] = _fid
            _picked = st.sidebar.multiselect(
                "Feeds to run (optional)",
                options=_labels,
                default=[],
                key="admin_feeds_supplier_pick",
                help="Leave empty to fetch & ingest **all** enabled feed sources. Pick one or more suppliers to pass `--feed-id` to `run_feeds.py`.",
            )
            for _lb in _picked:
                feed_id_extra.extend(["--feed-id", str(_id_by_label[_lb])])
        else:
            st.sidebar.caption(
                "No enabled rows in **`supplier_feed_sources`** (or DB unreachable). Run will use `--from-db` only.",
            )
    fetch_only = st.sidebar.checkbox(
        "Fetch only (`--fetch-only`)",
        value=False,
        key="admin_feeds_fetch_only",
        help="Download files but do not run `main.py` ingest.",
    )
    verbose = st.sidebar.checkbox("Verbose (`-v`)", value=False, key="admin_feeds_verbose")
    st.sidebar.caption(
        "Stamped feed ingest (default): **prunes** offers not in this file, updates rows only when **price or stock** "
        "changes, **stock > 0** only, skips **no/zero price**. Override below to append or include out‑of‑stock lines."
    )
    append_offers = st.sidebar.checkbox(
        "Append offers (keep previous vendor rows)",
        value=False,
        key="admin_feeds_append_offers",
        help="Passes `--no-offer-snapshot` to `run_feeds.py` (do not delete existing offers before insert).",
    )
    include_zero_stock = st.sidebar.checkbox(
        "Include zero / missing stock rows",
        value=False,
        key="admin_feeds_include_zero_stock",
        help="Passes `--include-zero-stock` (ingest lines without stock or with quantity 0).",
    )
    config_rel = "feeds_config.json"
    if not use_from_db:
        config_rel = st.sidebar.text_input(
            "Feeds JSON path",
            value="feeds_config.json",
            key="admin_feeds_config_path",
            help="Relative to the project root, or an absolute path.",
        )
    run_btn = st.sidebar.button(
        "Run run_feeds.py",
        type="primary",
        use_container_width=True,
        key="admin_feeds_run_btn",
    )

    if run_btn:
        root = Path(__file__).resolve().parent
        script = root / "run_feeds.py"
        if not script.is_file():
            st.session_state["_admin_last_feed_run"] = {
                "exit": -1,
                "log": f"Missing {script.name} next to admin_app.py (expected {script}).",
                "cmd": "",
            }
        else:
            cmd: list[str] = [sys.executable, str(script)]
            if use_from_db:
                cmd.append("--from-db")
                cmd.extend(feed_id_extra)
            else:
                c = (config_rel or "").strip()
                if c:
                    cmd.extend(["--config", c])
            if fetch_only:
                cmd.append("--fetch-only")
            if verbose:
                cmd.append("-v")
            if append_offers:
                cmd.append("--no-offer-snapshot")
            if include_zero_stock:
                cmd.append("--include-zero-stock")
            try:
                completed = subprocess.run(
                    cmd,
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=3600,
                    env=os.environ.copy(),
                )
                parts: list[str] = []
                if completed.stdout:
                    parts.append(completed.stdout.rstrip())
                if completed.stderr:
                    parts.append("--- stderr ---\n" + completed.stderr.rstrip())
                st.session_state["_admin_last_feed_run"] = {
                    "exit": completed.returncode,
                    "log": "\n\n".join(parts) if parts else "(no output)",
                    "cmd": " ".join(cmd),
                }
            except subprocess.TimeoutExpired:
                st.session_state["_admin_last_feed_run"] = {
                    "exit": -2,
                    "log": "Process timed out after 1 hour.",
                    "cmd": " ".join(cmd),
                }
            except OSError as exc:
                st.session_state["_admin_last_feed_run"] = {
                    "exit": -3,
                    "log": str(exc),
                    "cmd": " ".join(cmd),
                }

    last = st.session_state.get("_admin_last_feed_run")
    if isinstance(last, dict) and last:
        ex = int(last.get("exit", -9))
        cmd_s = str(last.get("cmd") or "")
        if cmd_s:
            st.sidebar.caption(f"Command: `{cmd_s}`")
        if ex == 0:
            st.sidebar.success("Last run completed with exit code 0.")
        elif ex == -1:
            st.sidebar.error("Last run failed: setup / missing script.")
        elif ex < 0:
            st.sidebar.warning(f"Last run issue (code {ex}).")
        else:
            st.sidebar.error(f"Last run exit code: {ex}")
        log = str(last.get("log") or "")
        if len(log) > 25000:
            log = "… (output truncated) …\n" + log[-25000:]
        with st.sidebar.expander("Last run output", expanded=(ex != 0)):
            st.code(log or "(empty)", language="text")


def _sidebar_db_status() -> None:
    st.sidebar.header("MySQL connection")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        st.sidebar.success("Connected to Hostinger MySQL (via `.env`).")
    except Exception as exc:
        st.sidebar.error("Cannot connect to database.")
        st.sidebar.caption(str(exc))


def _vendor_name_choices_for_ingest() -> list[str]:
    """Distinct trimmed supplier names from ``vendor_offers`` and ``supplier_registry`` (FMS profiles)."""
    seen: dict[str, bool] = {}
    ordered: list[str] = []
    try:
        engine = get_engine()
        with engine.connect() as conn:
            q1 = text(
                "SELECT DISTINCT TRIM(vendor_name) AS v FROM vendor_offers "
                "WHERE vendor_name IS NOT NULL AND CHAR_LENGTH(TRIM(vendor_name)) > 0",
            )
            for row in conn.execute(q1).fetchall():
                v = (row[0] or "").strip()
                if v and v not in seen:
                    seen[v] = True
                    ordered.append(v)
            try:
                q2 = text(
                    "SELECT DISTINCT TRIM(vendor_name) AS v FROM supplier_registry "
                    "WHERE vendor_name IS NOT NULL AND CHAR_LENGTH(TRIM(vendor_name)) > 0",
                )
                for row in conn.execute(q2).fetchall():
                    v = (row[0] or "").strip()
                    if v and v not in seen:
                        seen[v] = True
                        ordered.append(v)
            except Exception:
                pass
        ordered.sort(key=str.casefold)
        return ordered
    except Exception:
        return []


def main() -> None:
    _sidebar_db_status()
    _sidebar_run_feeds()

    st.title("B2B catalog — admin ingest")
    st.caption(
        "Upload **CSV**, **TSV**, **TXT** (tab, comma, or semicolon-separated), or **Excel**, "
        "then map columns and ingest into the same DB as `main.py`."
    )

    ingest_mode = st.radio(
        "What are you uploading?",
        (INGEST_VENDOR_LABEL, INGEST_MASTER_LABEL),
        horizontal=False,
        key="admin_ingest_mode",
        help="**Vendor catalog** creates `vendor_offers` with prices. **Master datasheet** only updates `master_products` and syncs titles/EAN/category onto matching `products` (append-only by MPN+Brand).",
    )
    is_master = ingest_mode == INGEST_MASTER_LABEL
    if st.session_state.get("_admin_prev_ingest_mode") != ingest_mode:
        st.session_state["_admin_prev_ingest_mode"] = ingest_mode
        for field in STANDARD_FIELDS:
            st.session_state.pop(f"admin_map_{field}", None)
        for field in MASTER_FIELDS:
            st.session_state.pop(f"admin_map_{field}", None)

    region = "EU"
    vendor_name = ""
    if not is_master:
        region = st.selectbox(
            "Region / currency",
            ("UK", "EU", "USA"),
            index=1,
            help="Your **Price** column is stored as the native column for this region, then **GBP, EUR, and USD** are all filled using fixed factors in `.env` (`B2B_FX_GBP_PER_EUR`, `B2B_FX_USD_PER_EUR`).",
        )
        st.caption(
            "FX pivot is **EUR**: GBP = EUR×`B2B_FX_GBP_PER_EUR`, USD = EUR×`B2B_FX_USD_PER_EUR` (defaults 0.86 and 1.08 if unset). "
            "Match the same variables in `index.php`’s `.env` for the catalog UI."
        )

        supplier_mode = st.radio(
            "Supplier name",
            ("Select existing vendor", "New supplier name"),
            horizontal=True,
            key="admin_supplier_mode",
            help="Stored on each offer as **`vendor_offers.vendor_name`**.",
        )
        if supplier_mode == "Select existing vendor":
            names = _vendor_name_choices_for_ingest()
            if names:
                opts = [""] + names
                pick = st.selectbox(
                    "Vendor",
                    options=opts,
                    index=0,
                    format_func=lambda x: "— Select supplier —" if x == "" else str(x),
                    key="admin_vendor_select",
                    help="Names from distinct **`vendor_offers.vendor_name`** and **`supplier_registry`** (Supplier management).",
                )
                vendor_name = (pick or "").strip()
            else:
                st.info(
                    "No supplier names in the database yet. Add **`supplier_registry`** rows in FMS or ingest offers first, "
                    "or use **New supplier name** below.",
                )
                vendor_name = st.text_input(
                    "Vendor name",
                    value="",
                    key="admin_vendor_existing_fallback",
                    placeholder="Type exact name for first-time ingest",
                )
        else:
            vendor_name = st.text_input(
                "New supplier name",
                value="",
                key="admin_vendor_new",
                placeholder="e.g. Alldis GmbH, Your distributor…",
            )
    else:
        st.info(
            "**Master datasheet:** full ingest maps to **`master_products`** (needs **Brand**, **Title**, and **MPN or EAN**). "
            "Use **Identifiers-only patch** (below the column map) to **fill EAN / ASIN / MPN** on rows that already exist — **no Brand or Title** required in the file; matching uses EAN, then MPN (+ optional Brand column if MPN is ambiguous), then ASIN/URL. "
            "Applies the same cleanup rules as **Master → Cleanup**. No **`vendor_offers`** are created."
        )

    uploaded = st.file_uploader(
        "Upload catalog file",
        type=["csv", "tsv", "txt", "xlsx", "xlsm"],
        help="`.tsv` uses tab. `.txt` separator is detected from the first line (tab vs `;` vs `,`).",
    )

    if uploaded is None:
        st.info("Upload a file to configure column mapping.")
        return

    key = f"{uploaded.name}-{uploaded.size}"
    need_load = st.session_state.get("admin_upload_key") != key or "admin_df" not in st.session_state
    if need_load:
        try:
            st.session_state["admin_df"] = _read_uploaded_df(uploaded.getvalue(), uploaded.name)
        except Exception as exc:
            st.session_state.pop("admin_upload_key", None)
            st.session_state.pop("admin_df", None)
            st.error("Could not read this file. Try saving as CSV (UTF-8) or Excel `.xlsx`.")
            st.caption(str(exc))
            return
        st.session_state["admin_upload_key"] = key
        for field in STANDARD_FIELDS:
            st.session_state.pop(f"admin_map_{field}", None)
        for field in MASTER_FIELDS:
            st.session_state.pop(f"admin_map_{field}", None)

    df: pd.DataFrame = st.session_state["admin_df"]
    if df.empty:
        st.warning("The file has no rows.")
        return

    cols = [str(c).strip() for c in df.columns]
    options = [_NONE] + cols

    st.subheader("Column mapping")
    if is_master:
        st.caption(
            "**Full ingest:** map **Brand** and **Title** (required), plus **MPN** and/or **EAN** (at least one). Optional: **Category**, **ASIN**, "
            "**Monthly sale on Amazon**, **Amazon URL**. **Master row ID** is only needed if you use that optional field during **Identifiers-only patch**. "
            "**Identifiers-only patch:** map **Master row ID** to the exported **`id`** column (from Master database download) to update the correct row regardless of EAN/MPN changes, "
            "and/or map **MPN**, **EAN**, **ASIN**, **Amazon URL** for lookup. You can also map **Title**, **Category**, **Brand** to push refined text into existing rows."
        )
        field_list = MASTER_FIELDS
        required_set = REQUIRED_MASTER
    else:
        st.caption(
            "Map each standard field to a column in your file. **MPN**, **Brand**, and **Price** are required. "
            "**Title** is trimmed to **15 words max** on ingest."
        )
        field_list = STANDARD_FIELDS
        required_set = REQUIRED_VENDOR

    mapping: dict[str, str | None] = {}
    columns = st.columns(2)
    for i, field in enumerate(field_list):
        with columns[i % 2]:
            choice = st.selectbox(
                f"**{field}**",
                options,
                key=f"admin_map_{field}",
                help=(
                    "Exported **`id`** from `master_products` (CSV/Excel download on the Master database tab). "
                    "Strongly recommended when you edited an export and want one-to-one row updates."
                    if field == "Master row ID"
                    else "Pick the column from your file that matches this field."
                ),
            )
            mapping[field] = None if choice == _NONE else choice

    master_identifiers_only = False
    master_update_existing = False
    master_u_ean = True
    master_u_asin = True
    master_u_sales = True
    master_u_mpn = False
    master_u_title = True
    master_u_category = True
    master_u_brand = False
    master_patch_fill_missing_only = True
    if is_master:
        master_identifiers_only = st.checkbox(
            "**Identifiers-only patch** — update **existing** `master_products` rows (by **Master row ID** and/or EAN / MPN / ASIN)",
            value=False,
            key="admin_master_id_patch_only",
            help="Match by **`master_products.id`** when **Master row ID** is mapped (e.g. edited export), or by **EAN**, **MPN** (+ optional **Brand**), **ASIN** / URL. "
            "Does **not** insert new master rows. Choose which columns to apply below (missing-only unless you turn on overwrite).",
        )

    if is_master and master_identifiers_only:
        st.subheader("Fields to apply")
        st.caption(
            "Map **Master row ID** and/or identifier columns plus any **Title**, **Category**, **Brand** columns above. "
            "By default values are written **only where the DB field is empty** (and the file cell is non-empty). "
            "Enable **Overwrite non-empty** to replace existing database text and identifiers from your file. "
            "Rows where **every selected column already matches** the database are **skipped** (no SQL update)."
        )
        master_update_existing = True
        master_patch_fill_missing_only = not st.checkbox(
            "**Overwrite non-empty** — replace existing database values from the file (not only blanks)",
            value=False,
            key="admin_master_patch_overwrite",
        )
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            master_u_ean = st.checkbox("EAN", value=True, key="admin_master_u_ean_patch")
        with c2:
            master_u_asin = st.checkbox("ASIN & Amazon URL", value=True, key="admin_master_u_asin_patch")
        with c3:
            master_u_sales = st.checkbox("Amazon monthly sales", value=True, key="admin_master_u_sales_patch")
        with c4:
            master_u_mpn = st.checkbox(
                "MPN (text)",
                value=True,
                key="admin_master_u_mpn_patch",
                help="Updates `master_products.mpn` and matching `products.mpn` when the text changes. Skipped if another row already uses the target MPN+Brand.",
            )
        c5, c6, c7, _ = st.columns(4)
        with c5:
            master_u_title = st.checkbox("Title", value=True, key="admin_master_u_title_patch")
        with c6:
            master_u_category = st.checkbox("Category", value=True, key="admin_master_u_category_patch")
        with c7:
            master_u_brand = st.checkbox(
                "Brand",
                value=False,
                key="admin_master_u_brand_patch",
                help="Changes catalog `products.brand` for matching rows. Skipped if the new MPN+Brand pair already exists on another master row.",
            )
    elif is_master:
        st.subheader("Existing master rows (full ingest)")
        st.caption(
            "When a sheet row matches **`master_products`** on **MPN + Brand** (trimmed, case-insensitive), "
            "choose whether to **overwrite** identifiers from the file instead of skipping that row."
        )
        master_update_existing = st.checkbox(
            "**Update EAN / ASIN / MPN (and related)** for rows that already exist in `master_products`",
            value=False,
            key="admin_master_update_existing",
            help="Match is case-insensitive on trimmed MPN and Brand. Non-empty values from your file overwrite only the field types you tick below.",
        )
        c1, c2, c3, c4 = st.columns(4)
        _dis = not master_update_existing
        with c1:
            master_u_ean = st.checkbox("EAN", value=True, key="admin_master_u_ean", disabled=_dis)
        with c2:
            master_u_asin = st.checkbox("ASIN & Amazon URL", value=True, key="admin_master_u_asin", disabled=_dis)
        with c3:
            master_u_sales = st.checkbox("Amazon monthly sales", value=True, key="admin_master_u_sales", disabled=_dis)
        with c4:
            master_u_mpn = st.checkbox(
                "MPN",
                value=False,
                key="admin_master_u_mpn",
                disabled=_dis,
                help="Also updates matching catalog `products.mpn` when the stored MPN text changes. Skipped if another master row already uses the target MPN+Brand.",
            )

    if is_master and master_identifiers_only:
        missing = []
        patch_has_lookup = (
            mapping.get("Master row ID") is not None
            or mapping.get("MPN") is not None
            or mapping.get("EAN") is not None
            or mapping.get("ASIN") is not None
            or mapping.get("Amazon URL") is not None
        )
        if not patch_has_lookup:
            st.warning(
                "Map **Master row ID** (recommended for an edited export) and/or at least one of **MPN**, **EAN**, **ASIN**, **Amazon URL** so rows can be matched."
            )
        missing_id_master = not patch_has_lookup
    else:
        missing = [f for f in required_set if mapping.get(f) is None]
        if missing:
            st.warning(f"Map these fields before processing: **{', '.join(missing)}**")

        missing_id_master = is_master and mapping.get("MPN") is None and mapping.get("EAN") is None
        if missing_id_master:
            st.warning("For master datasheet, map **MPN** or **EAN** (at least one).")

    can_process = not missing and not missing_id_master
    if not can_process:
        st.caption("**Process & ingest** stays disabled until required columns are mapped.")

    if st.button(
        "Process & ingest",
        type="primary",
        disabled=not can_process,
        use_container_width=True,
    ):
        engine = get_engine()
        bar = st.progress(0.0, text="Starting…")
        time.sleep(0.02)
        try:
            if is_master:
                def _master_db_progress(p: float, msg: str) -> None:
                    bar.progress(0.15 + p * 0.84, text=msg)
                    time.sleep(0.001)

                if master_identifiers_only:
                    patches = _collect_master_identifier_patches_from_df(df, mapping, bar)
                    if not patches:
                        bar.empty()
                        st.error(
                            "No rows with a usable lookup (need **Master row ID** and/or EAN, MPN, ASIN, or Amazon URL on each line)."
                        )
                        return
                    stats = {
                        "added": 0,
                        "skipped": 0,
                        "updated_master": 0,
                        "not_found": 0,
                        "ambiguous": 0,
                        "mpn_update_skipped": 0,
                        "brand_update_skipped": 0,
                        "updated_products": 0,
                        "inserted_products": 0,
                    }
                    with Session(engine) as session:
                        stats = ingest_master_identifier_patches(
                            session,
                            patches,
                            chunk_size=500,
                            insert_batch_size=1,
                            on_progress=_master_db_progress,
                            update_ean=master_u_ean,
                            update_asin=master_u_asin,
                            update_amazon_monthly_sales=master_u_sales,
                            update_mpn=master_u_mpn,
                            update_title=master_u_title,
                            update_category=master_u_category,
                            update_brand=master_u_brand,
                            fill_missing_only=master_patch_fill_missing_only,
                        )
                        session.commit()
                    bar.progress(1.0, text="Done.")
                    parts = [
                        f"**Identifier patch:** updated **{stats['updated_master']}** master row(s)",
                        f"**{stats.get('not_found', 0)}** not matched",
                        f"**{stats.get('ambiguous', 0)}** ambiguous (multiple DB rows)",
                        f"**{stats['skipped']}** no column changes selected",
                    ]
                    if stats.get("mpn_update_skipped", 0):
                        parts.append(
                            f"**{stats['mpn_update_skipped']}** MPN update(s) skipped (conflict)",
                        )
                    if stats.get("brand_update_skipped", 0):
                        parts.append(
                            f"**{stats['brand_update_skipped']}** brand update(s) skipped (MPN+Brand conflict)",
                        )
                    st.success(
                        "; ".join(parts)
                        + f". Catalog: updated **{stats['updated_products']}** product(s), "
                        f"created **{stats['inserted_products']}**."
                    )
                    return

                rows_out, incomplete_out = _collect_master_rows_from_df(df, mapping, bar)
                Base.metadata.create_all(bind=engine, tables=[MasterIncompleteRow.__table__])
                n_queued = 0
                if incomplete_out:
                    with Session(engine) as session:
                        n_queued = queue_master_incomplete_rows(session, incomplete_out)
                        session.commit()

                if not rows_out and n_queued == 0:
                    bar.empty()
                    st.error("No non-empty data rows in file.")
                    return

                stats = {
                    "added": 0,
                    "skipped": 0,
                    "updated_master": 0,
                    "mpn_update_skipped": 0,
                    "updated_products": 0,
                    "inserted_products": 0,
                }
                if rows_out:
                    with Session(engine) as session:
                        stats = ingest_master_datasheet(
                            session,
                            rows_out,
                            chunk_size=500,
                            insert_batch_size=64,
                            on_progress=_master_db_progress,
                            update_existing_master=master_update_existing,
                            update_ean=master_u_ean,
                            update_asin=master_u_asin,
                            update_amazon_monthly_sales=master_u_sales,
                            update_mpn=master_u_mpn,
                        )
                        session.commit()
                bar.progress(1.0, text="Done.")
                done_parts = [
                    f"**Master:** added **{stats['added']}** row(s)",
                    f"updated **{stats.get('updated_master', 0)}** existing row(s)",
                    f"skipped **{stats['skipped']}** (duplicates / no changes)",
                ]
                if stats.get("mpn_update_skipped", 0):
                    done_parts.append(
                        f"**{stats['mpn_update_skipped']}** MPN update(s) skipped (target MPN+Brand conflict)",
                    )
                st.success(
                    "; ".join(done_parts)
                    + f". **{n_queued}** incomplete row(s) saved for **Master database → Incomplete rows**. "
                    f"Catalog: updated **{stats['updated_products']}** product(s), created **{stats['inserted_products']}**."
                )
                return

            vn_raw = (vendor_name or "").strip()
            if not vn_raw:
                bar.empty()
                st.error("Enter a **Vendor name** before processing.")
                return

            rows_out = []
            for _, row in df.iterrows():
                d = _build_row_dict(row, mapping, region)
                if d is not None:
                    rows_out.append(d)

            if not rows_out:
                bar.empty()
                st.error("No valid rows (need non-empty MPN, Brand, and numeric Price per row).")
                return

            total_inserted = 0
            chunks = [rows_out[i : i + CHUNK_ROWS] for i in range(0, len(rows_out), CHUNK_ROWS)]
            for i, chunk in enumerate(chunks):
                with Session(engine) as session:
                    matcher = ProductMatcher(session)
                    n = matcher.ingest_vendor_catalog(vn_raw, chunk, chunk_size=500)
                    session.commit()
                    total_inserted += n
                bar.progress((i + 1) / len(chunks), text=f"Batch {i + 1}/{len(chunks)}…")
            bar.progress(1.0, text="Done.")
            st.success(
                f"**{total_inserted}** offer row(s) written to the database "
                f"(`{len(rows_out)}` valid rows from file; remainder skipped if MPN/Brand/Price empty).",
            )
        except Exception as exc:
            bar.empty()
            st.exception(exc)


main()
