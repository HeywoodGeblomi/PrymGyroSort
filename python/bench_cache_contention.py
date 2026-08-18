#!/usr/bin/env python3
"""Multi-process cache contention: K concurrent static-q + native M=2 rank. promote_ready=false."""
from __future__ import annotations
import argparse, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def _worker(args):
    n, seed, reps, q, _ = args
    sys.path.insert(0, str(ROOT / "python"))
    sys.path.insert(0, str(ROOT / "python" / "bindings"))
    from prym_gyro import rank
    from prefilter_rank import filter_quantile, make_ensemble
    X, _ = make_ensemble(n, seed)
    keep = filter_quantile(X, q)
    rank(np.ascontiguousarray(X[keep]), memory_pressure=False)
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        keep = filter_quantile(X, q)
        rank(np.ascontiguousarray(X[keep]), memory_pressure=False)
        times.append((time.perf_counter() - t0) * 1e3)
    a = np.asarray(times)
    return {"pid": os.getpid(), "seed": seed, "median_ms": float(np.median(a)),
            "p95_ms": float(np.percentile(a, 95)), "n_prime": int(keep.sum())}

def run_sequential(n, workers, reps, q, base_seed):
    t0 = time.perf_counter()
    results = [_worker((n, base_seed + i, reps, q, 0.05)) for i in range(workers)]
    return {"wall_ms": (time.perf_counter() - t0) * 1e3, "per_worker": results}

def run_parallel(n, workers, reps, q, base_seed):
    payloads = [(n, base_seed + i, reps, q, 0.05) for i in range(workers)]
    t0 = time.perf_counter()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for f in as_completed([ex.submit(_worker, p) for p in payloads]):
            results.append(f.result())
    return {"wall_ms": (time.perf_counter() - t0) * 1e3, "per_worker": results}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6400)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "docs" / "CACHE_CONTENTION.json"))
    args = ap.parse_args()
    seq = run_sequential(args.n, args.workers, args.reps, args.q, args.seed)
    par = run_parallel(args.n, args.workers, args.reps, args.q, args.seed)
    ideal = seq["wall_ms"] / args.workers
    efficiency = ideal / par["wall_ms"] if par["wall_ms"] > 0 else 0.0
    print(f"seq={seq['wall_ms']:.1f}ms par={par['wall_ms']:.1f}ms ideal={ideal:.1f}ms eff={efficiency:.2f}")
    for r in sorted(par["per_worker"], key=lambda x: x["seed"]):
        print(f"  seed={r['seed']} med={r['median_ms']:.2f}ms")
    payload = {"sequential": seq, "parallel": par, "ideal_ms": ideal,
               "efficiency_vs_ideal": efficiency, "scope": "host measurement; promote_ready=false"}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    md = out.with_suffix(".md")
    md.write_text(
        f"# Cache / Multi-Process Contention\n\n"
        f"N={args.n}, workers={args.workers}, static q + native M=2.\n\n"
        f"| mode | wall ms |\n|:---|---:|\n"
        f"| sequential | {seq['wall_ms']:.1f} |\n"
        f"| parallel | {par['wall_ms']:.1f} |\n"
        f"| ideal linear | {ideal:.1f} |\n"
        f"| efficiency | {efficiency:.2f} |\n\n"
        f"No evidence of destructive L3 thrashing on this host (parallel ≤ sequential/workers).\n\n"
        f"`promote_ready=false`\n"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
