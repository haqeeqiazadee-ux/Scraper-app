"""Load supplier feed definitions from FMS table ``fms_fms_supplier_feed_sources`` (Supabase PostgreSQL)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine


def _slug_path_component(s: str, feed_id: int) -> str:
    t = re.sub(r"[^a-zA-Z0-9._-]+", "_", (s or "").strip())
    t = t.strip("._-") or "supplier"
    return f"{feed_id}_{t}"


def row_to_fetch_dict(row: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Map DB row to :func:`feeds.download.fetch_source` + ingest options."""
    rid = int(row["id"])
    protocol = str(row.get("protocol") or "sftp").strip().lower()
    if protocol == "ftps":
        proto_api = "ftp"
        use_tls = True
    else:
        proto_api = protocol
        use_tls = bool(int(row.get("use_tls") or 0))

    base = str(row.get("local_basename") or "feed.csv").strip() or "feed.csv"
    if not base.lower().endswith(".csv"):
        base = f"{base}.csv"
    rel = Path("data") / "feeds" / f"{_slug_path_component(str(row.get('vendor_name') or ''), rid)}_{base}"
    local_abs = project_root / rel

    src: dict[str, Any] = {
        "id": f"fms_{rid}",
        "_db_id": rid,
        "protocol": proto_api,
        "use_tls": use_tls,
        "host": (row.get("host") or "").strip(),
        "local_path": str(local_abs),
        "run_ingest": bool(int(row.get("run_ingest", 1))),
        "stamp_ingest": bool(int(row.get("stamp_ingest", 1))),
        "zip_inner_pattern": (row.get("zip_inner_pattern") or "*.csv").strip() or "*.csv",
    }

    pw = row.get("password_plain")
    if pw is not None and str(pw) != "":
        src["password"] = str(pw)

    port = row.get("port")
    if port is not None and str(port).strip() != "":
        src["port"] = int(port)

    user = (row.get("username") or "").strip()
    if user:
        src["username"] = user

    rp = row.get("remote_path")
    if rp is not None and str(rp).strip() != "":
        src["remote_path"] = str(rp).strip()
    else:
        rd = row.get("remote_dir")
        if rd is not None and str(rd).strip() != "":
            src["remote_dir"] = str(rd).strip()
        pat = row.get("remote_pattern")
        if pat is not None and str(pat).strip() != "":
            src["remote_pattern"] = str(pat).strip()

    sk = (row.get("sftp_private_key_path") or "").strip()
    if sk:
        src["private_key_path_value"] = sk

    if protocol == "url":
        src["protocol"] = "url"
        src["http_url"] = (row.get("http_url") or "").strip()
        env_key = (row.get("ingest_csv_env_key") or "VENDOR_A_CSV_PATH").strip() or "VENDOR_A_CSV_PATH"
        vname = (row.get("vendor_name") or "").strip() or "Vendor A"
        src["ingest_env"] = {
            env_key: str(local_abs.resolve()),
            "VENDOR_A_NAME": vname,
            "VENDOR_A_STAMP_INGEST": "1" if src["stamp_ingest"] else "0",
        }
        src["ingest_argv"] = None
        return src

    if protocol == "imap":
        src["protocol"] = "imap"
        src["imap_host"] = src.pop("host", "")
        if "port" in src:
            src["imap_port"] = src.pop("port")
        src["imap_user"] = user
        src["imap_folder"] = (row.get("imap_folder") or "INBOX").strip() or "INBOX"
        sc = (row.get("imap_subject_contains") or "").strip()
        if sc:
            src["subject_contains"] = sc
        sd = (row.get("imap_sender_contains") or "").strip()
        if sd:
            src["sender_contains"] = sd
        src["search_unseen_only"] = bool(int(row.get("search_unseen_only", 1)))
        src["mark_seen"] = bool(int(row.get("mark_seen", 1)))
        exts = (row.get("attachment_extensions") or ".csv,.zip").strip()
        src["attachment_extensions"] = [x.strip() for x in exts.split(",") if x.strip()]
        src.pop("host", None)
        src.pop("port", None)
        src.pop("use_tls", None)

    env_key = (row.get("ingest_csv_env_key") or "VENDOR_A_CSV_PATH").strip() or "VENDOR_A_CSV_PATH"
    vname = (row.get("vendor_name") or "").strip() or "Vendor A"
    src["ingest_env"] = {
        env_key: str(local_abs.resolve()),
        "VENDOR_A_NAME": vname,
        "VENDOR_A_STAMP_INGEST": "1" if src["stamp_ingest"] else "0",
    }
    src["ingest_argv"] = None
    return src


def list_enabled_feed_sources(engine: Engine) -> list[dict[str, Any]]:
    """Return enabled rows for UI pickers: ``id``, ``vendor_name``, ``protocol``."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, vendor_name, protocol FROM fms_supplier_feed_sources "
                "WHERE enabled = TRUE ORDER BY vendor_name ASC, id ASC",
            ),
        ).mappings().all()
    return [dict(r) for r in rows]


def load_enabled_sources(
    engine: Engine,
    project_root: Path,
    *,
    feed_ids: Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        if feed_ids is not None:
            ids = sorted({int(i) for i in feed_ids if int(i) > 0})
            if not ids:
                return []
            stmt = text(
                "SELECT * FROM fms_supplier_feed_sources WHERE enabled = TRUE AND id IN :ids "
                "ORDER BY vendor_name ASC",
            ).bindparams(bindparam("ids", expanding=True))
            rows = conn.execute(stmt, {"ids": ids}).mappings().all()
        else:
            rows = conn.execute(
                text(
                    "SELECT * FROM fms_supplier_feed_sources WHERE enabled = TRUE ORDER BY vendor_name ASC",
                ),
            ).mappings().all()
    return [row_to_fetch_dict(dict(r), project_root) for r in rows]


def update_run_status(engine: Engine, feed_id: int, ok: bool, message: str, max_len: int = 500) -> None:
    msg = (message or "").strip()
    if len(msg) > max_len:
        msg = msg[: max_len - 3] + "..."
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE fms_supplier_feed_sources SET last_run_at = NOW(), "
                "last_run_ok = :ok, last_run_message = :msg WHERE id = :id",
            ),
            {"ok": 1 if ok else 0, "msg": msg, "id": feed_id},
        )
