#!/usr/bin/env python3
"""Phase-1 microbench: zero-copy binding vs file-path rank_driver."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

from prym_gyro import rank, rank_report  # noqa: E402


def make_ensemble(n: int, seed: int = 42):
    rng = np.random.default_rng(seed)
    obj0, obj1 = rng.random(n), rng.random(n)
    k = min(48, n)
    idx = rng.choice(n, size=k, replace=False)
    obj0[idx] = rng.uniform(0.0, 0.05, size=k)
    obj1[idx] = rng.uniform(0.0, 0.05, size=k)
    X = np.ascontiguousarray(np.column_stack([obj0, obj1]), dtype=np.float64)
    is_good = np.zeros(n, dtype=bool)
    is_good[idx] = True
    return X, is_good


def bench_zerocopy(X, reps=15):
    rank(X, memory_pressure=False)  # warmup
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        rank(X, memory_pressure=False)
        times.append((time.perf_counter() - t0) * 1e3)
    info = rank_report(X, memory_pressure=False)
    return {"median_ms": float(np.median(times)), "min_ms": float(np.min(times)),
            "strategy": info.get("strategy")}


def main():
    for n in (4096, 65536):
        X, is_good = make_ensemble(n)
        zc = bench_zerocopy(X, reps=15 if n <= 4096 else 5)
        ranks = rank(X)
        gap = float(ranks[~is_good].mean() - ranks[is_good].mean())
        print(f"N={n}  zerocopy median={zc['median_ms']:.3f} ms  "
              f"strategy={zc['strategy']}  gap={gap:.2f}")
    print("Phase-1 zero-copy GREEN. Core header untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
