#!/usr/bin/env python3
"""Download supplier catalog files (SFTP, FTP, IMAP, or HTTP URL) and run ``main.py`` ingest.

* **JSON:** default ``feeds_config.json`` (or ``FEEDS_CONFIG`` env).
* **FMS database:** ``python run_feeds.py --from-db`` reads enabled rows from MySQL table
  ``supplier_feed_sources`` (configure in FMS → **Feed sources**). Limit to specific rows::

    python run_feeds.py --from-db --feed-id 3
    python run_feeds.py --from-db --feed-id 1 --feed-id 2

Schedule (cron / Task Scheduler) from the project directory::

    python run_feeds.py --from-db

HTTPS issues: ``pip install certifi`` (included in requirements) fixes many ``CERTIFICATE_VERIFY_FAILED`` cases on Windows.
If handshake still fails, set ``FEED_HTTP_SSL_LEGACY=1``. **Insecure last resort:** ``FEED_HTTP_SSL_NO_VERIFY=1`` (disables cert check).

**Stamped ingest** (when ``stamp_ingest`` is enabled on a source, the default from FMS): each run sets
``FEED_INGEST_TIMESTAMP_ISO`` and, unless you override in ``ingest_env`` or pass ``--no-offer-snapshot`` /
``--include-zero-stock``, also ``VENDOR_OFFERS_SNAPSHOT=1`` (drop ``vendor_offers`` rows not in this feed;
existing rows are updated only when **price or stock** changes) and ``VENDOR_A_IN_STOCK_ONLY=1`` (CSV
rows need stock column > 0). Rows with no or non-positive **price** are skipped.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from feeds.config import load_feeds_config
from feeds.download import fetch_source


def _run_ingest(project_root: Path, src: dict, stamp_iso: str) -> int:
    argv = list(src.get("ingest_argv") or [sys.executable, "main.py"])
    if argv and argv[0].lower() in ("python", "python3"):
        argv[0] = sys.executable
    env = os.environ.copy()
    for k, v in (src.get("ingest_env") or {}).items():
        env[str(k)] = str(v)
    if src.get("stamp_ingest", True):
        env.setdefault("FEED_INGEST_TIMESTAMP_ISO", stamp_iso)
        env.setdefault("VENDOR_OFFERS_SNAPSHOT", "1")
        env.setdefault("VENDOR_A_IN_STOCK_ONLY", "1")
    logging.info("Running ingest: %s", " ".join(argv))
    r = subprocess.run(argv, cwd=str(project_root), env=env)
    return int(r.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch supplier feeds and ingest into MySQL.")
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Load enabled definitions from MySQL table supplier_feed_sources (FMS).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to feeds JSON (with --from-db unused unless JSON fallback).",
    )
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Download files only; do not run main.py",
    )
    parser.add_argument(
        "--feed-id",
        action="append",
        type=int,
        dest="feed_ids",
        metavar="ID",
        help="With --from-db, only this supplier_feed_sources id (repeat for several). Omit for all enabled.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--no-offer-snapshot",
        action="store_true",
        help="Do not delete existing vendor_offers before ingest (append mode). Overrides stamped ingest default.",
    )
    parser.add_argument(
        "--include-zero-stock",
        action="store_true",
        help="Ingest CSV rows with missing or zero stock. Overrides VENDOR_A_IN_STOCK_ONLY default on stamped feeds.",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    load_dotenv()
    if args.no_offer_snapshot:
        os.environ["VENDOR_OFFERS_SNAPSHOT"] = "0"
    if args.include_zero_stock:
        os.environ["VENDOR_A_IN_STOCK_ONLY"] = "0"

    project_root = Path(__file__).resolve().parent
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    engine = None
    sources: list = []
    if args.from_db:
        from core.database import get_engine
        from feeds.db_sources import load_enabled_sources, update_run_status

        engine = get_engine()
        id_filter = list(dict.fromkeys(args.feed_ids or []))
        sources = load_enabled_sources(engine, project_root, feed_ids=id_filter or None)
        if id_filter and not sources:
            logging.warning(
                "No enabled supplier_feed_sources rows matched --feed-id %s (wrong id or disabled).",
                id_filter,
            )
            return 0
        if not id_filter and not sources:
            logging.warning("No enabled rows in supplier_feed_sources (FMS → Feed sources).")
            return 0
        if id_filter and sources:
            found = {int(s["_db_id"]) for s in sources if s.get("_db_id") is not None}
            missing = [i for i in id_filter if int(i) not in found]
            if missing:
                logging.warning(
                    "No enabled supplier_feed_sources row for id(s) (skipped): %s",
                    missing,
                )
    else:
        cfg_path = args.config or Path(os.environ.get("FEEDS_CONFIG", "feeds_config.json"))
        if not cfg_path.is_absolute():
            cfg_path = project_root / cfg_path
        try:
            cfg = load_feeds_config(cfg_path)
        except FileNotFoundError:
            logging.error(
                "Missing %s — use --from-db or copy feeds_config.example.json.",
                cfg_path,
            )
            return 2
        except (json.JSONDecodeError, ValueError) as exc:
            logging.error("Invalid config %s: %s", cfg_path, exc)
            return 2
        sources = cfg.get("sources") or []

    exit_code = 0
    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            logging.warning("Skipping invalid source entry %s", i)
            continue
        sid = str(src.get("id") or f"source_{i}")
        db_id = src.get("_db_id")
        try:
            logging.info("Fetching [%s] protocol=%s", sid, src.get("protocol"))
            out = fetch_source(src, project_root)
            logging.info("Saved [%s] -> %s", sid, out)
        except Exception as exc:
            logging.exception("Fetch failed [%s]: %s", sid, exc)
            if engine is not None and db_id:
                try:
                    from feeds.db_sources import update_run_status

                    update_run_status(engine, int(db_id), False, str(exc) or traceback.format_exc()[-500:])
                except Exception:
                    logging.exception("Could not update last_run status in DB")
            exit_code = 1
            continue
        if args.fetch_only:
            if engine is not None and db_id:
                try:
                    from feeds.db_sources import update_run_status

                    update_run_status(engine, int(db_id), True, "Fetched OK (fetch-only)")
                except Exception:
                    pass
            continue
        if not src.get("run_ingest", True):
            if engine is not None and db_id:
                try:
                    from feeds.db_sources import update_run_status

                    update_run_status(engine, int(db_id), True, "Fetched OK (ingest skipped)")
                except Exception:
                    pass
            continue
        rc = _run_ingest(project_root, src, stamp)
        if engine is not None and db_id:
            try:
                from feeds.db_sources import update_run_status

                msg = "Ingest OK" if rc == 0 else f"Ingest failed exit={rc}"
                update_run_status(engine, int(db_id), rc == 0, msg)
            except Exception:
                logging.exception("Could not update last_run status in DB")
        if rc != 0:
            logging.error("Ingest failed [%s] exit=%s", sid, rc)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
