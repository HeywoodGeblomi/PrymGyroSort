#!/usr/bin/env python3
"""
GYR-SIEVE-001 Track 1 — Pair sieve CLI

Two numeric objectives. Calls GyroRank (no Python Fenwick reimplementation).
Emits required report keys including identity_ok / identity_sha256 vs Fenwick.
Default: no geometric prefilter. promote_ready=false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

VERSION = "0.1.0-pair-sieve"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

try:
    from prym_gyro import rank
except Exception as e:
    print(json.dumps({"error": "native_binding_unavailable", "detail": str(e)}), file=sys.stderr)
    raise SystemExit(3)


def die(code: int, msg: str, *, as_json: bool = False) -> None:
    payload = {"ok": False, "error": msg, "exit_code": code, "version": VERSION, "promote_ready": False}
    print(json.dumps(payload) if as_json else f"[pair_sieve] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def validate_matrix(X: np.ndarray, *, as_json: bool = False) -> np.ndarray:
    if not isinstance(X, np.ndarray):
        die(2, "matrix is not a numpy array", as_json=as_json)
    if X.ndim != 2:
        die(2, f"matrix must be 2-D (N,2); got ndim={X.ndim}", as_json=as_json)
    if X.shape[0] < 1:
        die(2, "matrix is empty (N=0)", as_json=as_json)
    if X.shape[1] != 2:
        die(2, f"matrix must have M=2 columns; got M={X.shape[1]}", as_json=as_json)
    X = np.ascontiguousarray(X, dtype=np.float64)
    if not np.isfinite(X).all():
        die(2, f"matrix contains non-finite values", as_json=as_json)
    return X


def load_matrix(path: str, n: int, *, as_json: bool = False) -> np.ndarray:
    p = Path(path)
    if not p.is_file():
        die(2, f"matrix file not found: {path}", as_json=as_json)
    raw = np.fromfile(p, dtype=np.float64)
    if raw.size != n * 2:
        die(2, f"matrix size mismatch: file has {raw.size} floats, expected {n * 2}", as_json=as_json)
    return validate_matrix(raw.reshape(n, 2), as_json=as_json)


def synthetic(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.ascontiguousarray(rng.random((n, 2), dtype=np.float64))


def ranks_sha256(ranks: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(ranks, dtype=np.int32).tobytes()).hexdigest()


def run_pair_sieve(X: np.ndarray, k: int = 1, *, as_json: bool = False) -> dict:
    X = validate_matrix(X, as_json=as_json)
    n = int(X.shape[0])
    if k < 1:
        die(1, f"k must be >= 1; got {k}", as_json=as_json)

    # Public entry (controller path → Fenwick on v0.2)
    t0 = time.perf_counter()
    ranks = rank(X, memory_pressure=False)
    wall_ms = (time.perf_counter() - t0) * 1e3

    # Identity: second call must be bit-identical (Fenwick-only on v0.2)
    ranks_ref = rank(X, memory_pressure=False)
    identity_ok = bool(np.array_equal(ranks, ranks_ref))
    identity_sha = ranks_sha256(ranks)

    front_size = int(np.sum(ranks == 1))
    front_k = int(np.sum(ranks <= k))

    return {
        "ok": True,
        "version": VERSION,
        "n": n,
        "wall_ms": round(wall_ms, 4),
        "front_size": front_size,
        "k": k,
        "front_k": front_k,
        "identity_sha256": identity_sha,
        "identity_ok": identity_ok,
        "strategy": "Fenwick2D",
        "promote_ready": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=f"GYR-SIEVE-001 pair sieve {VERSION}")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--matrix", default=None, help="path to matrix.bin (N*2 float64)")
    ap.add_argument("--n", type=int, default=100_000, help="row count (default 1e5 for S1)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--k", type=int, default=1, help="max rank kept (default 1 = front)")
    ap.add_argument("--out", default=None, help="optional output directory")
    args = ap.parse_args()
    as_json = bool(args.json)

    if args.version:
        print(json.dumps({"version": VERSION, "promote_ready": False}) if as_json else VERSION)
        return 0

    if args.n < 1 or args.n > 5_000_000:
        die(1, f"n out of range: {args.n}", as_json=as_json)

    try:
        if args.matrix:
            X = load_matrix(args.matrix, args.n, as_json=as_json)
            source = str(args.matrix)
        else:
            X = synthetic(args.n, args.seed)
            source = f"synthetic_seed={args.seed}"

        report = run_pair_sieve(X, k=args.k, as_json=as_json)
        report["source"] = source

        if as_json:
            print(json.dumps(report))
        else:
            print(
                f"[pair_sieve] n={report['n']} wall_ms={report['wall_ms']:.3f} "
                f"front_size={report['front_size']} k={report['k']} "
                f"identity_ok={report['identity_ok']} strategy={report['strategy']} "
                f"promote_ready=false"
            )
            if not report["identity_ok"]:
                print("[pair_sieve] FAIL identity_ok=false", file=sys.stderr)
                return 4

        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            ranks = rank(X, memory_pressure=False)
            np.save(out / "ranks.npy", ranks)
            (out / "report.json").write_text(json.dumps(report, indent=2))

        return 0 if report["identity_ok"] else 4
    except SystemExit:
        raise
    except Exception as e:
        print(
            json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}", "exit_code": 3, "promote_ready": False})
            if as_json
            else f"[pair_sieve] ERROR: {e}",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
