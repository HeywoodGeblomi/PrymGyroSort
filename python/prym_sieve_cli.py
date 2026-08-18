#!/usr/bin/env python3
"""PrymGyroSort production sieve CLI — M=2 quantile + native rank. promote_ready=false."""
from __future__ import annotations
import argparse, json, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from prefilter_rank import filter_quantile, make_ensemble  # noqa: E402
from prym_gyro import rank  # noqa: E402

def load_matrix(path, n, m=2):
    raw = np.fromfile(path, dtype=np.float64)
    if raw.size != n * m:
        raise SystemExit(f"matrix size {raw.size} != n*m={n*m}")
    return np.ascontiguousarray(raw.reshape(n, m))

def run_once(X, q, top_frac):
    t0 = time.perf_counter()
    if q is not None:
        keep = filter_quantile(X, q)
        idx = np.flatnonzero(keep)
        ranks_p = rank(np.ascontiguousarray(X[idx]), memory_pressure=X.shape[0] >= 65536)
        ranks = np.full(X.shape[0], 10**9, dtype=np.int32)
        ranks[idx] = ranks_p
        n_prime, path = int(idx.size), f"quantile_q={q}"
    else:
        ranks = rank(X, memory_pressure=X.shape[0] >= 65536)
        n_prime, path = X.shape[0], "full"
    ms = (time.perf_counter() - t0) * 1e3
    top_k = max(1, int(top_frac * X.shape[0]))
    order = np.argsort(ranks, kind="stable")
    top = order[:top_k]
    return {"n": int(X.shape[0]), "n_prime": n_prime, "path": path, "ms": ms,
            "top_indices": top.tolist(), "top_ranks": ranks[top].tolist(),
            "min_rank": int(ranks.min())}

def _worker(payload):
    n, seed, q, top_frac = payload
    X, _ = make_ensemble(n, seed)
    return run_once(X, q, top_frac)

def main():
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
    print(f"[sieve] M=2 n={args.n} prefilter={'off' if q is None else f'q={q}'} workers={args.workers} promote_ready=false")
    if args.workers > 1:
        if args.matrix:
            raise SystemExit("--workers>1 requires synthetic (no --matrix)")
        t0 = time.perf_counter()
        reports = []
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            for f in as_completed([ex.submit(_worker, (args.n, args.seed + i, q, args.top_frac)) for i in range(args.workers)]):
                reports.append(f.result())
        wall = (time.perf_counter() - t0) * 1e3
        for i, r in enumerate(reports):
            print(f"  worker path={r['path']} n'={r['n_prime']} ms={r['ms']:.3f}")
        print(f"[sieve] parallel wall={wall:.2f} ms")
        if args.out:
            out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
            (out / "report.json").write_text(json.dumps({"workers": args.workers, "wall_ms": wall, "reports": reports,
                "scope": "execution sieve only; promote_ready=false"}, indent=2))
        return 0
    X = load_matrix(Path(args.matrix), args.n) if args.matrix else make_ensemble(args.n, args.seed)[0]
    report = run_once(X, q, args.top_frac)
    report["scope"] = "execution sieve only; promote_ready=false; not alpha"
    print(f"[sieve] path={report['path']} n'={report['n_prime']} ms={report['ms']:.3f} min_rank={report['min_rank']}")
    if args.out:
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        if q is not None:
            keep = filter_quantile(X, q); idx = np.flatnonzero(keep)
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
