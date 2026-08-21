#!/usr/bin/env python3
"""
GYR-SIEVE-001 pair sieve CLI (Track 1 + Track 2 χ + Track 3 prefilter)

Two numeric objectives. Calls GyroRank (no Python Fenwick reimplementation).
--prefilter off by default (S7: off ≡ Track 1).
--chi off by default.
promote_ready=false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

VERSION = "0.3.0-pair-sieve-prefilter"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

from prefilter import apply_prefilter, run_falsifier, PREFILTER_NAME, DEFAULT_Q  # Track 3


def die(code: int, msg: str, *, as_json: bool = False) -> None:
    payload = {"ok": False, "error": msg, "exit_code": code, "version": VERSION, "promote_ready": False}
    print(json.dumps(payload) if as_json else f"[pair_sieve] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _load_rank():
    try:
        from prym_gyro import rank
        return rank
    except Exception as e:
        print(json.dumps({"error": "native_binding_unavailable", "detail": str(e)}), file=sys.stderr)
        raise SystemExit(3)


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
        die(2, "matrix contains non-finite values", as_json=as_json)
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


def run_pair_sieve(
    X: np.ndarray,
    k: int = 1,
    *,
    prefilter: str | None = None,
    prefilter_q: float = DEFAULT_Q,
    chi: bool = False,
    chi_seed: int = 0,
    as_json: bool = False,
) -> dict:
    rank_fn = _load_rank()
    from chi_pick import chi_pick  # Track 2
    X_full = validate_matrix(X, as_json=as_json)
    n_full = int(X_full.shape[0])
    if k < 1:
        die(1, f"k must be >= 1; got {k}", as_json=as_json)

    n_dropped = 0
    if prefilter:
        X, mask = apply_prefilter(X_full, name=prefilter, q=prefilter_q)
        n_dropped = int(n_full - X.shape[0])
        if X.shape[0] < 1:
            die(2, "prefilter dropped all rows", as_json=as_json)
        X = validate_matrix(X, as_json=as_json)
    else:
        X = X_full

    n = int(X.shape[0])

    t0 = time.perf_counter()
    ranks = rank_fn(X, memory_pressure=False)
    wall_ms = (time.perf_counter() - t0) * 1e3
    ranks = np.ascontiguousarray(ranks, dtype=np.int32)

    ranks_ref = np.ascontiguousarray(rank_fn(X, memory_pressure=False), dtype=np.int32)
    identity_ok = bool(np.array_equal(ranks, ranks_ref))
    sha = ranks_sha256(ranks)

    front_size = int(np.sum(ranks == 1))
    F = [int(i) for i in np.flatnonzero(ranks <= k)]

    report = {
        "ok": True,
        "version": VERSION,
        "n": n,
        "wall_ms": round(wall_ms, 4),
        "front_size": front_size,
        "k": int(k),
        "identity_sha256": sha,
        "identity_ok": identity_ok,
        "strategy": "Fenwick2D",
        "promote_ready": False,
    }

    if prefilter:
        report["prefilter"] = prefilter
        report["prefilter_q"] = float(prefilter_q)
        report["n_full"] = n_full
        report["n_dropped"] = n_dropped
        report["n_survivors"] = n

    if chi:
        try:
            chi_result = chi_pick(F, seed=chi_seed)
            pick = chi_result["pick"]
            if pick not in F:
                die(4, f"chi pick {pick} not in F", as_json=as_json)
            if ranks_sha256(ranks) != sha:
                die(4, "chi path mutated ranks (S5 fail)", as_json=as_json)
            report["chi_on"] = True
            report["chi_pick"] = int(pick)
            report["chi_token"] = chi_result["chi_token"]
            report["chi_seed"] = int(chi_seed)
        except ValueError as e:
            die(4, str(e), as_json=as_json)

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=f"GYR-SIEVE-001 pair sieve {VERSION}")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--matrix", default=None, help="path to matrix.bin (N*2 float64)")
    ap.add_argument("--n", type=int, default=100_000, help="row count (default 1e5 for S1)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--k", type=int, default=1, help="max rank kept (default 1 = front)")
    ap.add_argument(
        "--prefilter",
        default="off",
        choices=["off", "or_quantile"],
        help="Track 3: named prefilter (default: off). or_quantile = bottom-q on obj0 OR obj1",
    )
    ap.add_argument("--q", type=float, default=DEFAULT_Q, help="or_quantile fraction (default 0.25)")
    ap.add_argument("--chi", action="store_true", help="Track 2: run χ pick on front F (off by default)")
    ap.add_argument("--chi-seed", type=int, default=0, help="documented seed/tape for χ pick")
    ap.add_argument("--falsifier", action="store_true", help="Track 3 S9: run named keep/drop falsifier and exit")
    ap.add_argument("--out", default=None, help="optional output directory")
    args = ap.parse_args()
    as_json = bool(args.json)

    if args.version:
        print(json.dumps({"version": VERSION, "promote_ready": False}) if as_json else VERSION)
        return 0

    if args.falsifier:
        result = run_falsifier(q=float(args.q))
        print(json.dumps(result, indent=2) if as_json else result)
        return 0 if result["falsifier_ok"] else 9

    if args.n < 1 or args.n > 5_000_000:
        die(1, f"n out of range: {args.n}", as_json=as_json)

    try:
        if args.matrix:
            X = load_matrix(args.matrix, args.n, as_json=as_json)
            source = str(args.matrix)
        else:
            X = synthetic(args.n, args.seed)
            source = f"synthetic_seed={args.seed}"

        pf = None if args.prefilter == "off" else args.prefilter
        report = run_pair_sieve(
            X,
            k=args.k,
            prefilter=pf,
            prefilter_q=float(args.q),
            chi=args.chi,
            chi_seed=args.chi_seed,
            as_json=as_json,
        )
        report["source"] = source

        if as_json:
            print(json.dumps(report))
        else:
            line = (
                f"[pair_sieve] n={report['n']} wall_ms={report['wall_ms']:.3f} "
                f"front_size={report['front_size']} k={report['k']} "
                f"identity_ok={report['identity_ok']} strategy={report['strategy']} "
                f"promote_ready=false"
            )
            if report.get("prefilter"):
                line += f" prefilter={report['prefilter']} dropped={report['n_dropped']}"
            if report.get("chi_on"):
                line += f" chi_pick={report['chi_pick']} chi_token={report['chi_token']}"
            print(line)
            if not report["identity_ok"]:
                print("[pair_sieve] FAIL identity_ok=false", file=sys.stderr)
                return 4

        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            Xp = X
            if pf:
                Xp, _ = apply_prefilter(X, name=pf, q=float(args.q))
            ranks = _load_rank()(Xp, memory_pressure=False)
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
