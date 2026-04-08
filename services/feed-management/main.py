"""Run all vendor ingest adapters against the configured MySQL database."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from adapters.vendor_a_csv import VendorACsvAdapter
from core.database import get_engine, init_db

Runner = Callable[[Session], int | None]


def run_vendor_a_csv(session: Session) -> int | None:
    """Ingest Vendor A CSV when ``VENDOR_A_CSV_PATH`` is set; otherwise skip."""
    label = "Vendor A (CSV)"
    path = (os.environ.get("VENDOR_A_CSV_PATH") or "").strip()
    if not path:
        print(f"{label}: skipped (set VENDOR_A_CSV_PATH in .env)", file=sys.stderr, flush=True)
        return None
    try:
        adapter = VendorACsvAdapter()
    except ValueError as exc:
        print(f"{label}: skipped ({exc})", file=sys.stderr, flush=True)
        return None
    print(
        f"{label}: reading CSV and writing to MySQL (remote hosts can take several minutes for large files)…",
        flush=True,
    )
    count = adapter.ingest(session)
    print(
        f"{label} [{adapter.vendor_name()}]: {count} offer row(s) inserted or updated",
        flush=True,
    )
    return count


# Register adapters here as you add new vendor modules.
RUNNERS: tuple[Runner, ...] = (
    run_vendor_a_csv,
    # run_vendor_b_api,
)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run B2B vendor ingest adapters.")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Create database tables if missing (SQLAlchemy metadata create_all).",
    )
    args = parser.parse_args()

    print("Connecting to database…", flush=True)
    engine = get_engine()
    if args.init_db:
        print("Creating tables if missing…", flush=True)
        init_db(engine)

    total_offers = 0
    ran = 0
    print("Running adapters…", flush=True)
    with Session(engine) as session:
        for runner in RUNNERS:
            inserted = runner(session)
            if inserted is not None:
                session.commit()
                total_offers += inserted
                ran += 1
            else:
                session.rollback()

    if ran == 0:
        print(
            "No adapters ran. Configure at least one source (e.g. VENDOR_A_CSV_PATH).",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print(
        f"Finished {ran} adapter(s); {total_offers} vendor offer row(s) inserted or updated this run.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
