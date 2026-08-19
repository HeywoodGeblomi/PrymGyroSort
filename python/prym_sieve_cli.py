#!/usr/bin/env python3
"""PrymGyroSort production sieve CLI v0.1.5-sieve — hardened. promote_ready=false."""
from __future__ import annotations
import argparse, json, sys, time, traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

VERSION = "0.1.5-sieve"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from prefilter_rank import filter_quantile, make_ensemble  # noqa: E402
try:
    from prym_gyro import rank
except Exception as e:
    print(json.dumps({"error": "native_binding_unavailable", "detail": str(e)}), file=sys.stderr)
    raise SystemExit(3)

def die(code, msg, *, as_json=False):
    payload = {"ok": False, "error": msg, "exit_code": code, "version": VERSION}
    print(json.dumps(payload) if as_json else f"[sieve] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)

def _ensemble(n, seed):
    out = make_ensemble(n, seed)
    return out[0] if isinstance(out, tuple) else out

def validate_matrix(X, *, as_json=False):
    if not isinstance(X, np.ndarray):
        die(2, "matrix is not a numpy array", as_json=as_json)
    if X.ndim != 2:
        die(2, f"matrix must be 2-D (N,2); got ndim={X.ndim}", as_json=as_json)
    if X.shape[0] < 1:
        die(2, "matrix is empty (N=0)", as_json=as_json)
    if X.shape[1] != 2:
        die(2, f"matrix must have M=2 columns; got M={X.shape[1]}", as_json=as_json)
    if X.dtype != np.float64:
        X = np.ascontiguousarray(X, dtype=np.float64)
    if not X.flags["C_CONTIGUOUS"]:
        X = np.ascontiguousarray(X, dtype=np.float64)
    if not np.isfinite(X).all():
        die(2, f"matrix contains non-finite values (nan={int(np.isnan(X).sum())}, inf={int(np.isinf(X).sum())})", as_json=as_json)
    return X

def load_matrix(path, n, m=2, *, as_json=False):
    path = Path(path)
    if not path.is_file():
        die(2, f"matrix file not found: {path}", as_json=as_json)
    raw = np.fromfile(path, dtype=np.float64)
    if raw.size != n * m:
        die(2, f"matrix size mismatch: file has {raw.size} floats, expected {n*m}", as_json=as_json)
    return validate_matrix(raw.reshape(n, m), as_json=as_json)

def run_once(X, q, top_frac, *, as_json=False):
    X = validate_matrix(X, as_json=as_json)
    if not (0.0 < top_frac <= 1.0):
        die(1, f"top_frac must be in (0,1]; got {top_frac}", as_json=as_json)
    if q is not None and not (0.0 < q <= 1.0):
        die(1, f"q must be in (0,1]; got {q}", as_json=as_json)
    t0 = time.perf_counter()
    try:
        if q is not None:
            keep = filter_quantile(X, q)
            idx = np.flatnonzero(keep)
            if idx.size == 0:
                die(2, "prefilter kept 0 rows — relax q", as_json=as_json)
            ranks_p = rank(np.ascontiguousarray(X[idx]), memory_pressure=X.shape[0] >= 65536)
            ranks = np.full(X.shape[0], 10**9, dtype=np.int32)
            ranks[idx] = ranks_p
            n_prime, path = int(idx.size), f"quantile_q={q}"
        else:
            ranks = rank(X, memory_pressure=X.shape[0] >= 65536)
            n_prime, path = X.shape[0], "full"
    except Exception as e:
        die(3, f"ranking failed: {type(e).__name__}: {e}", as_json=as_json)
    ms = (time.perf_counter() - t0) * 1e3
    top_k = max(1, int(top_frac * X.shape[0]))
    order = np.argsort(ranks, kind="stable")
    top = order[:top_k]
    return {"ok": True, "version": VERSION, "n": int(X.shape[0]), "n_prime": n_prime, "path": path,
            "ms": round(ms, 4), "top_indices": top.tolist(), "top_ranks": ranks[top].tolist(),
            "min_rank": int(ranks.min()), "promote_ready": False}

def _worker(payload):
    n, seed, q, top_frac = payload
    return run_once(_ensemble(n, seed), q, top_frac)

def self_check(*, as_json=False):
    checks = []
    try:
        X = validate_matrix(_ensemble(256, 7))
        checks.append({"name": "ensemble_shape", "ok": X.shape == (256, 2)})
        r = run_once(X, 0.25, 0.05)
        checks.append({"name": "quantile_rank", "ok": r["min_rank"] >= 1 and r["n_prime"] > 0})
        r2 = run_once(X, None, 0.05)
        checks.append({"name": "full_rank", "ok": r2["n_prime"] == 256})
        bad = X.copy(); bad[0, 0] = np.nan
        try:
            validate_matrix(bad)
            checks.append({"name": "reject_nan", "ok": False})
        except SystemExit as e:
            checks.append({"name": "reject_nan", "ok": e.code == 2})
    except Exception as e:
        if as_json: print(json.dumps({"ok": False, "error": str(e), "checks": checks}))
        return 4
    ok = all(c["ok"] for c in checks)
    payload = {"ok": ok, "version": VERSION, "checks": checks, "promote_ready": False}
    if as_json: print(json.dumps(payload, indent=2))
    else:
        for c in checks: print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}")
        print(f"[sieve] self-check {'PASS' if ok else 'FAIL'} version={VERSION}")
    return 0 if ok else 4

def main():
    ap = argparse.ArgumentParser(description=f"PrymGyroSort {VERSION}")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--matrix", default=None)
    ap.add_argument("--n", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--no-prefilter", action="store_true")
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    as_json = bool(args.json)
    if args.version:
        print(json.dumps({"version": VERSION, "promote_ready": False}) if as_json else VERSION); return 0
    if args.self_check: return self_check(as_json=as_json)
    if args.n < 1 or args.n > 5_000_000: die(1, f"n out of range: {args.n}", as_json=as_json)
    if args.workers < 1 or args.workers > 64: die(1, f"workers out of range: {args.workers}", as_json=as_json)
    q = None if args.no_prefilter else args.q
    if not as_json:
        print(f"[sieve] {VERSION} M=2 n={args.n} prefilter={'off' if q is None else f'q={q}'} workers={args.workers} promote_ready=false")
    try:
        if args.workers > 1:
            if args.matrix: die(1, "--workers>1 requires synthetic", as_json=as_json)
            t0 = time.perf_counter(); reports = []
            with ProcessPoolExecutor(max_workers=args.workers) as ex:
                for f in as_completed([ex.submit(_worker, (args.n, args.seed+i, q, args.top_frac)) for i in range(args.workers)]):
                    reports.append(f.result())
            wall = (time.perf_counter()-t0)*1e3
            summary = {"ok": True, "version": VERSION, "workers": args.workers, "wall_ms": round(wall,3), "reports": reports, "promote_ready": False}
            print(json.dumps(summary) if as_json else f"[sieve] parallel wall={wall:.2f} ms")
            if args.out:
                Path(args.out).mkdir(parents=True, exist_ok=True)
                (Path(args.out)/"report.json").write_text(json.dumps(summary, indent=2))
            return 0
        X = load_matrix(args.matrix, args.n, as_json=as_json) if args.matrix else validate_matrix(_ensemble(args.n, args.seed), as_json=as_json)
        report = run_once(X, q, args.top_frac, as_json=as_json)
        report["source"] = str(args.matrix) if args.matrix else f"synthetic_seed={args.seed}"
        if as_json: print(json.dumps(report))
        else:
            print(f"[sieve] path={report['path']} n'={report['n_prime']} ms={report['ms']} min_rank={report['min_rank']}")
        if args.out:
            out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
            if q is not None:
                keep = filter_quantile(X, q); idx = np.flatnonzero(keep)
                ranks = np.full(X.shape[0], 10**9, dtype=np.int32)
                ranks[idx] = rank(np.ascontiguousarray(X[idx]))
            else: ranks = rank(X)
            np.save(out/"ranks.npy", ranks)
            (out/"report.json").write_text(json.dumps(report, indent=2))
        return 0
    except SystemExit: raise
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}", "exit_code": 3}) if as_json else f"[sieve] ERROR: {e}", file=sys.stderr)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
