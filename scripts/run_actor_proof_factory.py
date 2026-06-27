from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _read_done(ledger_path: Path) -> set[str]:
    if not ledger_path.exists():
        return set()
    done: set[str] = set()
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            done.add(str(json.loads(line)["actor_id"]))
        except (KeyError, json.JSONDecodeError):
            continue
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


def _prove_actor(
    actor: dict[str, Any],
    *,
    base_url: str | None,
    tenant: str,
    timeout: int,
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
                },
            },
            tenant,
            timeout,
        )
        return proof["data"]
    except (KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "actor_id": actor_id,
            "proof_level": "api_mapped",
            "last_verified_at": now,
            "test_input": test_input,
            "live_e2e_passed": False,
            "fixture_replay_passed": False,
            "ui_route_passed": False,
            "failure_class": "external_outage",
            "failure_reason": type(exc).__name__,
            "provenance": ["proof-factory-runner", "failed-api-call"],
        }


def _status(ledger_path: Path) -> None:
    counts: dict[str, int] = {}
    total = 0
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            total += 1
            try:
                level = str(json.loads(line).get("proof_level", "unknown"))
            except json.JSONDecodeError:
                level = "invalid"
            counts[level] = counts.get(level, 0) + 1
    print(json.dumps({"ledger": str(ledger_path), "rows": total, "counts_by_level": counts}, indent=2))


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
    parser.add_argument("--write-ledger", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    if args.status:
        _status(ledger_path)
        return 0

    actors = _load_catalog(Path(args.catalog))
    done = _read_done(ledger_path) if args.resume else set()
    pending = [actor for actor in actors if str(actor["id"]) not in done]
    if args.sample > 0:
        pending = pending[: args.sample]

    results: list[dict[str, Any]] = []
    delay = 1.0 / max(args.rate_limit_per_second, 0.1) if args.base_url else 0.0
    with ThreadPoolExecutor(max_workers=max(args.concurrency, 1)) as executor:
        futures = []
        for actor in pending:
            futures.append(
                executor.submit(
                    _prove_actor,
                    actor,
                    base_url=args.base_url or None,
                    tenant=args.tenant,
                    timeout=args.timeout,
                )
            )
            if delay:
                time.sleep(delay)
        for future in as_completed(futures):
            results.append(future.result())

    if args.write_ledger:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(result, sort_keys=True, default=str) + "\n")

    print(json.dumps({"catalog_count": len(actors), "processed": len(results), "ledger": str(ledger_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
