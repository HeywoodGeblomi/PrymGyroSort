#!/usr/bin/env python3
"""PrymGyroSort production sieve CLI — M=2 quantile + native rank. promote_ready=false."""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

from prefilter_rank import filter_quantile, make_ensemble  # noqa: E402
from prym_gyro import rank  # noqa: E402


def _ensemble(n: int, seed: int) -> np.ndarray:
    """Return (N, 2) matrix. Tolerates make_ensemble returning X or (X, meta)."""
    out = make_ensemble(n, seed)
    if isinstance(out, tuple):
        return out[0]
    return out


def load_matrix(path: Path, n: int, m: int = 2) -> np.ndarray:
    raw = np.fromfile(path, dtype=np.float64)
    if raw.size != n * m:
        raise SystemExit(f"[sieve] matrix size {raw.size} != n*m={n*m}")
    return np.ascontiguousarray(raw.reshape(n, m))


def run_once(X: np.ndarray, q: float | None, top_frac: float) -> dict:
    if X.ndim != 2 or X.shape[1] != 2:
        raise ValueError(f"expected (N,2) matrix, got {X.shape}")
    t0 = time.perf_counter()
    if q is not None:
        keep = filter_quantile(X, q)
        idx = np.flatnonzero(keep)
        ranks_p = rank(np.ascontiguousarray(X[idx]), memory_pressure=X.shape[0] >= 65536)
        ranks = np.full(X.shape[0], fill_value=10**9, dtype=np.int32)
        ranks[idx] = ranks_p
        n_prime = int(idx.size)
        path = f"quantile_q={q}"
    else:
        ranks = rank(X, memory_pressure=X.shape[0] >= 65536)
        n_prime = X.shape[0]
        path = "full"
    ms = (time.perf_counter() - t0) * 1e3
    top_k = max(1, int(top_frac * X.shape[0]))
    order = np.argsort(ranks, kind="stable")
    top = order[:top_k]
    return {
        "n": int(X.shape[0]),
        "n_prime": n_prime,
        "path": path,
        "ms": ms,
        "top_indices": top.tolist(),
        "top_ranks": ranks[top].tolist(),
        "min_rank": int(ranks.min()),
    }


def _worker(payload: tuple) -> dict:
    n, seed, q, top_frac = payload
    return run_once(_ensemble(n, seed), q, top_frac)


def main() -> int:
    ap = argparse.ArgumentParser(description="PrymGyroSort sieve CLI (promote_ready=false)")
    ap.add_argument("--matrix", default=None)
    ap.add_argument("--n", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--no-prefilter", action="store_true")
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    q = None if args.no_prefilter else args.q

    print(
        f"[sieve] M=2  n={args.n}  prefilter={'off' if q is None else f'q={q}'}  "
        f"workers={args.workers}  promote_ready=false"
    )

    if args.workers > 1:
        if args.matrix:
            raise SystemExit("--workers>1 requires synthetic (no --matrix)")
        t0 = time.perf_counter()
        reports = []
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs = [
                ex.submit(_worker, (args.n, args.seed + i, q, args.top_frac))
                for i in range(args.workers)
            ]
            for f in as_completed(futs):
                reports.append(f.result())
        wall = (time.perf_counter() - t0) * 1e3
        for i, r in enumerate(reports):
            print(f"  worker path={r['path']} n'={r['n_prime']} ms={r['ms']:.3f}")
        print(f"[sieve] parallel wall={wall:.2f} ms")
        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            (out / "report.json").write_text(
                json.dumps(
                    {"workers": args.workers, "wall_ms": wall, "reports": reports,
                     "scope": "execution sieve only; promote_ready=false"},
                    indent=2,
                )
            )
        return 0

    if args.matrix:
        X = load_matrix(Path(args.matrix), args.n)
        source = str(args.matrix)
    else:
        X = _ensemble(args.n, args.seed)
        source = f"synthetic_seed={args.seed}"

    report = run_once(X, q, args.top_frac)
    report["source"] = source
    report["scope"] = "execution sieve only; promote_ready=false; not alpha"
    print(
        f"[sieve] path={report['path']}  n'={report['n_prime']}  "
        f"ms={report['ms']:.3f}  min_rank={report['min_rank']}"
    )
    print(f"[sieve] top[{args.top_frac:.0%}] indices={report['top_indices'][:10]}...")

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        if q is not None:
            keep = filter_quantile(X, q)
            idx = np.flatnonzero(keep)
            ranks = np.full(X.shape[0], 10**9, dtype=np.int32)
            ranks[idx] = rank(np.ascontiguousarray(X[idx]))
        else:
            ranks = rank(X)
        np.save(out / "ranks.npy", ranks)
        (out / "report.json").write_text(json.dumps(report, indent=2))
        print(f"[sieve] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
