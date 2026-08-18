#!/usr/bin/env python3
"""Parallel binding-iron: concurrent illegal layout attacks must all raise. promote_ready=false."""
from __future__ import annotations
import argparse, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def _attack_battery(seed):
    sys.path.insert(0, str(ROOT / "python" / "bindings"))
    sys.path.insert(0, str(ROOT / "python"))
    import prym_gyro_native as native
    from prym_gyro import rank as py_rank
    rng = np.random.default_rng(seed)
    n = 256
    results = {"pid": os.getpid(), "seed": seed, "legal_ok": 0, "illegal_caught": 0, "illegal_missed": 0}
    def expect_raise(fn):
        try:
            fn(); results["illegal_missed"] += 1; return False
        except Exception:
            results["illegal_caught"] += 1; return True
    def expect_ok(fn):
        try:
            fn(); results["legal_ok"] += 1; return True
        except Exception:
            return False
    for _ in range(20):
        X = np.ascontiguousarray(rng.standard_normal((n, 2)), dtype=np.float64)
        ranks = np.empty(n, dtype=np.int32)
        expect_ok(lambda: native.rank(X, ranks, False))
        expect_ok(lambda: py_rank(X))
        expect_raise(lambda: native.rank(np.ascontiguousarray(rng.standard_normal((n, 3))), ranks, False))
        expect_raise(lambda: native.rank(np.asfortranarray(rng.standard_normal((n, 2)).astype(np.float64)), ranks, False))
        messy = np.ascontiguousarray(rng.standard_normal((n, 4)), dtype=np.float64)[:, ::2]
        expect_raise(lambda: native.rank(messy, ranks.copy(), False))
        expect_raise(lambda: native.rank(np.ascontiguousarray(rng.standard_normal((n, 2)), dtype=np.float32), ranks, False))
        expect_raise(lambda: native.rank(X, np.empty(n // 2, dtype=np.int32), False))
    results["pass"] = results["illegal_missed"] == 0 and results["legal_ok"] == 40
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "docs" / "PARALLEL_IRON.json"))
    args = ap.parse_args()
    t0 = time.perf_counter()
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for f in as_completed([ex.submit(_attack_battery, args.seed + i) for i in range(args.workers)]):
            results.append(f.result())
    wall = (time.perf_counter() - t0) * 1e3
    all_pass = all(r["pass"] for r in results)
    total_caught = sum(r["illegal_caught"] for r in results)
    total_missed = sum(r["illegal_missed"] for r in results)
    total_legal = sum(r["legal_ok"] for r in results)
    print(f"legal={total_legal} caught={total_caught} missed={total_missed} ALL_PASS={all_pass}")
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results, "totals": {"legal_ok": total_legal,
        "illegal_caught": total_caught, "illegal_missed": total_missed, "all_pass": all_pass},
        "wall_ms": wall, "scope": "concurrent binding stress; promote_ready=false"}, indent=2))
    md = out.with_suffix(".md")
    md.write_text(f"# Parallel Binding Iron\n\n**ALL_PASS={all_pass}** — illegal={total_caught} caught, {total_missed} missed, legal={total_legal}\n\n`promote_ready=false`\n")
    return 0 if all_pass else 1

if __name__ == "__main__":
    raise SystemExit(main())
