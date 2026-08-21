#!/usr/bin/env python3
"""GYR-HOOK-001 F3 — live path with external options.csv.

probe-emit is F2-skipped. Caller supplies options.csv (two honest scores per option).
Flow: checksum(data) → hook rank → checksum(data) [must match] → record chosen_id
      → optional single talent invoke (after chosen_id is recorded).

Does not invent Photonic scores. Does not edit gyro_rank.hpp.
promote_ready=false.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

VERSION = "0.1.0-hook-f3"


def array_checksum(a: np.ndarray) -> str:
    x = np.ascontiguousarray(a)
    return hashlib.sha256(x.tobytes()).hexdigest()


def load_data_array(path: Path | None, n: int, seed: int) -> np.ndarray:
    if path is not None:
        raw = np.fromfile(path, dtype=np.int64)
        if raw.size < 1:
            raise SystemExit("[live] data file empty")
        return np.ascontiguousarray(raw)
    rng = np.random.default_rng(seed)
    return np.ascontiguousarray(rng.integers(0, 1_000_000, size=n, dtype=np.int64))


def run_hook(csv_path: Path, *, chi: bool, chi_seed: int) -> dict:
    """In-process fenwick_oracle path (same as python/hook/run.py)."""
    run_path = ROOT / "python" / "hook" / "run.py"
    spec = importlib.util.spec_from_file_location("hook_run", run_path)
    hook_run = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(hook_run)

    ids, X = hook_run.load_menu(csv_path)
    X = hook_run.apply_senses(X, "lower", "lower")
    from prym_gyro import rank, rank_fenwick_ref

    ranks = np.ascontiguousarray(rank(X, memory_pressure=False), dtype=np.int32)
    ranks_ref = np.ascontiguousarray(rank_fenwick_ref(X), dtype=np.int32)
    identity_ok = bool(np.array_equal(ranks, ranks_ref))
    sha = hashlib.sha256(ranks.tobytes()).hexdigest()
    front_idx = [i for i in range(len(ids)) if ranks[i] == 1]
    chosen_ids = [ids[i] for i in front_idx]
    if not chosen_ids:
        raise SystemExit("[live] |F|==0 fail-closed")

    report = {
        "ok": True,
        "version": VERSION,
        "n_opt": len(ids),
        "front_size": len(chosen_ids),
        "chosen_ids": chosen_ids,
        "identity_ok": identity_ok,
        "identity_sha256": sha,
        "identity_mode": "fenwick_oracle",
        "promote_ready": False,
        "source": f"csv:{csv_path}",
    }

    if chi:
        from chi_pick import chi_pick

        chi_result = chi_pick(front_idx, seed=chi_seed)
        pick_i = int(chi_result["pick"])
        report.update(
            chi_on=True,
            chi_pick=ids[pick_i],
            chosen_id=ids[pick_i],
            chi_token=chi_result["chi_token"],
            chi_seed=int(chi_seed),
        )
    elif len(chosen_ids) == 1:
        report["chosen_id"] = chosen_ids[0]
    else:
        report["chosen_id"] = chosen_ids[0]
        report["chosen_id_note"] = "first of F; use --chi for irreversible pick"

    return report


def invoke_talent(chosen_id: str, data: np.ndarray) -> dict:
    """Invoke exactly one talent by id AFTER chosen_id is recorded.

    Without F2 Photonic emit, talents are caller-defined string tokens.
    Default: stable sort in-place as a stand-in single action (documented).
    Real Photonic residual dispatch can replace this map later without changing the hook.
    """
    before = array_checksum(data)
    data.sort()
    after = array_checksum(data)
    return {
        "invoked": chosen_id,
        "checksum_before_sort": before,
        "checksum_after_sort": after,
        "sorted": True,
        "note": "stand-in sort after chosen_id; replace with Photonic residual map when honest emit exists",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Hook live path {VERSION}")
    ap.add_argument("--csv", required=True, help="external options.csv (id,score0,score1)")
    ap.add_argument("--data", default=None, help="optional int64 binary array; else synthetic")
    ap.add_argument("--n", type=int, default=1024, help="synthetic array length if no --data")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--chi", action="store_true")
    ap.add_argument("--chi-seed", type=int, default=0)
    ap.add_argument("--invoke", action="store_true", help="run one talent after chosen_id recorded")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="write live report JSON")
    args = ap.parse_args()

    data = load_data_array(Path(args.data) if args.data else None, args.n, args.seed)
    ck_before = array_checksum(data)

    report = run_hook(Path(args.csv), chi=args.chi, chi_seed=args.chi_seed)
    ck_after_rank = array_checksum(data)
    rank_stable = ck_before == ck_after_rank

    report["data_checksum_before_rank"] = ck_before
    report["data_checksum_after_rank"] = ck_after_rank
    report["checksum_stable_through_rank"] = rank_stable
    report["version"] = VERSION

    if not rank_stable:
        report["ok"] = False
        if args.json:
            print(json.dumps(report))
        else:
            print("[live] FAIL: data checksum changed during rank", file=sys.stderr)
        return 4

    chosen = report.get("chosen_id") or (report["chosen_ids"][0] if report["chosen_ids"] else None)
    report["chosen_id"] = chosen

    if args.invoke and chosen is not None:
        report["invoke"] = invoke_talent(chosen, data)

    if args.json:
        print(json.dumps(report))
    else:
        print(
            f"[live] chosen_id={chosen} identity_ok={report['identity_ok']} "
            f"mode={report['identity_mode']} checksum_stable={rank_stable} "
            f"promote_ready=false"
        )
        if report.get("invoke"):
            print(f"[live] invoked={report['invoke']['invoked']} sorted={report['invoke']['sorted']}")

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2))

    return 0 if report.get("identity_ok") and rank_stable else 4


if __name__ == "__main__":
    raise SystemExit(main())
