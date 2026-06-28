from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.core.actor_runtime.proof import generate_actor_test_input


DEFAULT_LEDGER = Path("docs/agent-sync/runtime/actor-proof-ledger.jsonl")


def _load_catalog(index_path: Path) -> list[dict[str, Any]]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    base = index_path.parent
    actors: list[dict[str, Any]] = []
    for i in range(int(index["chunk_count"])):
        actors.extend(json.loads((base / f"chunk-{i}.json").read_text(encoding="utf-8")))
    return actors


def _safe_input(actor: dict[str, Any]) -> dict[str, Any]:
    return generate_actor_test_input(
        SimpleNamespace(
            actor_id=actor.get("id"),
            name=actor.get("name", "actor"),
            title=actor.get("title", ""),
            description=actor.get("description", ""),
            categories=tuple(actor.get("categories", []) or ()),
            route_strategy=actor.get("route_strategy", "native_pipeline"),
        )
    )


def _is_fixture_input(test_input: dict[str, Any]) -> bool:
    return bool(test_input.get("fixture_kind"))


def _is_successful_proof(row: dict[str, Any]) -> bool:
    return (
        str(row.get("failure_class", "none")) == "none"
        and str(row.get("proof_level"))
        in {
            "runtime_smoke_passed",
            "fixture_replay_passed",
            "ui_route_passed",
            "live_e2e_passed",
        }
    )


def _read_latest(ledger_path: Path) -> dict[str, dict[str, Any]]:
    if not ledger_path.exists():
        return {}
    latest: dict[str, dict[str, Any]] = {}
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            latest[str(row["actor_id"])] = row
        except (KeyError, json.JSONDecodeError):
            continue
    return latest


def _read_done(ledger_path: Path, *, success_only: bool = False) -> set[str]:
    latest = _read_latest(ledger_path)
    if not success_only:
        return set(latest)
    done: set[str] = set()
    for actor_id, row in latest.items():
        if _is_successful_proof(row):
            done.add(actor_id)
    return done


def _post_json(url: str, payload: dict[str, Any], tenant: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Tenant-ID": tenant},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _error_summary(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTPError:{exc.code}"
    return type(exc).__name__


def _write_ledger_row(handle: Any, result: dict[str, Any]) -> None:
    handle.write(json.dumps(result, sort_keys=True, default=str) + "\n")
    handle.flush()


def _prove_actor(
    actor: dict[str, Any],
    *,
    base_url: str | None,
    tenant: str,
    timeout: int,
    attempts: int,
    retry_backoff_seconds: float,
) -> dict[str, Any]:
    actor_id = str(actor["id"])
    test_input = _safe_input(actor)
    now = datetime.now(UTC).isoformat()
    if not base_url:
        return {
            "actor_id": actor_id,
            "proof_level": "api_mapped",
            "last_verified_at": now,
            "test_input": test_input,
            "live_e2e_passed": False,
            "fixture_replay_passed": False,
            "ui_route_passed": False,
            "failure_class": "none",
            "provenance": ["catalog-chunk", "offline-proof-runner"],
        }
    max_attempts = max(attempts, 1)
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            run = _post_json(
                f"{base_url.rstrip('/')}/api/v1/actors/{actor_id}/runs",
                {"input": test_input, "options": {"source": "proof_factory_runner"}},
                tenant,
                timeout,
            )
            run_id = run["data"]["run"]["id"]
            fixture_replay_passed = _is_fixture_input(test_input)
            proof = _post_json(
                f"{base_url.rstrip('/')}/api/v1/actors/{actor_id}/runs/{run_id}/proof",
                {
                    "ui_route_passed": False,
                    "fixture_replay_passed": fixture_replay_passed,
                    "provenance": ["proof-factory-runner", f"run:{run_id}"],
                    "proof_metadata": {
                        "input_kind": "hosted_fixture" if fixture_replay_passed else "external_target",
                        "fixture_kind": test_input.get("fixture_kind"),
                        "attempt": attempt,
                    },
                },
                tenant,
                timeout,
            )
            return proof["data"]
        except (KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < max_attempts:
                time.sleep(max(retry_backoff_seconds, 0.0) * attempt)

    return {
        "actor_id": actor_id,
        "proof_level": "api_mapped",
        "last_verified_at": now,
        "test_input": test_input,
        "live_e2e_passed": False,
        "fixture_replay_passed": False,
        "ui_route_passed": False,
        "failure_class": "external_outage",
        "failure_reason": _error_summary(last_exc) if last_exc else "unknown",
        "provenance": ["proof-factory-runner", "failed-api-call"],
        "proof_metadata": {
            "attempts": max_attempts,
            "input_kind": "hosted_fixture" if _is_fixture_input(test_input) else "external_target",
            "fixture_kind": test_input.get("fixture_kind"),
        },
    }


def _status(ledger_path: Path) -> None:
    counts: dict[str, int] = {}
    raw_rows = 0
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw_rows += 1
    latest = _read_latest(ledger_path)
    for row in latest.values():
        level = str(row.get("proof_level", "unknown"))
        counts[level] = counts.get(level, 0) + 1
    print(
        json.dumps(
            {
                "ledger": str(ledger_path),
                "rows": len(latest),
                "raw_rows": raw_rows,
                "counts_by_level": counts,
            },
            indent=2,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Resumable actor proof factory runner")
    parser.add_argument("--catalog", default="apps/web/public/data/actors/index.json")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument("--base-url", default="")
    parser.add_argument("--tenant", default="proof-factory")
    parser.add_argument("--sample", type=int, default=25)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--rate-limit-per-second", type=float, default=2.0)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--retry-backoff-seconds", type=float, default=2.0)
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        default=0.0,
        help="Stop scheduling new actors after this many seconds; in-flight proofs finish and flush.",
    )
    parser.add_argument("--write-ledger", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--resume-success-only", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    if args.status:
        _status(ledger_path)
        return 0

    actors = _load_catalog(Path(args.catalog))
    done = _read_done(ledger_path, success_only=args.resume_success_only) if args.resume else set()
    pending = [actor for actor in actors if str(actor["id"]) not in done]
    if args.sample > 0:
        pending = pending[: args.sample]

    results: list[dict[str, Any]] = []
    delay = 1.0 / max(args.rate_limit_per_second, 0.1) if args.base_url else 0.0
    ledger_handle = None
    started_at = time.monotonic()
    deadline = started_at + args.max_runtime_seconds if args.max_runtime_seconds > 0 else None
    stopped_due_to_deadline = False
    try:
        if args.write_ledger:
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger_handle = ledger_path.open("a", encoding="utf-8")

        workers = max(args.concurrency, 1)
        actor_iter = iter(pending)
        actor_source_exhausted = False

        def deadline_reached() -> bool:
            return deadline is not None and time.monotonic() >= deadline

        with ThreadPoolExecutor(max_workers=workers) as executor:
            in_flight = set()

            def submit_next() -> bool:
                nonlocal actor_source_exhausted, stopped_due_to_deadline
                if actor_source_exhausted:
                    return False
                if deadline_reached():
                    stopped_due_to_deadline = True
                    return False
                try:
                    actor = next(actor_iter)
                except StopIteration:
                    actor_source_exhausted = True
                    return False
                in_flight.add(
                    executor.submit(
                        _prove_actor,
                        actor,
                        base_url=args.base_url or None,
                        tenant=args.tenant,
                        timeout=args.timeout,
                        attempts=args.attempts,
                        retry_backoff_seconds=args.retry_backoff_seconds,
                    )
                )
                if delay:
                    time.sleep(delay)
                return True

            while len(in_flight) < workers and submit_next():
                pass

            while in_flight:
                done_futures, in_flight = wait(in_flight, timeout=0.5, return_when=FIRST_COMPLETED)
                if not done_futures:
                    if deadline_reached():
                        stopped_due_to_deadline = True
                    continue
                for future in done_futures:
                    result = future.result()
                    results.append(result)
                    if ledger_handle is not None:
                        _write_ledger_row(ledger_handle, result)
                while len(in_flight) < workers and submit_next():
                    pass
    finally:
        if ledger_handle is not None:
            ledger_handle.close()

    print(
        json.dumps(
            {
                "catalog_count": len(actors),
                "processed": len(results),
                "pending_remaining": max(len(pending) - len(results), 0),
                "stopped_due_to_deadline": stopped_due_to_deadline,
                "ledger": str(ledger_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
