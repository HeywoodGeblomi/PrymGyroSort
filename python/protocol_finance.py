#!/usr/bin/env python3
"""Finance protocol adapter v0.1.5 — multi-profile structural sieve. promote_ready=false."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ADAPTER_VERSION = "0.1.5"
PROFILES = ("pairs", "liquidity", "stress", "micro")


def _norm(x: np.ndarray) -> np.ndarray:
    lo, hi = float(np.min(x)), float(np.max(x))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-15:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def synthetic_market(n: int, seed: int, n_good: int = 48):
    if n < 1:
        raise ValueError("n must be >= 1")
    rng = np.random.default_rng(seed)
    dislocation = np.abs(rng.normal(0.3, 0.4, size=n))
    obi = rng.uniform(-1.0, 1.0, size=n)
    bid_ask = np.abs(rng.normal(0.05, 0.03, size=n)) + 0.001
    depth = np.abs(rng.normal(8000.0, 4000.0, size=n)) + 100.0
    mdd = np.abs(rng.normal(0.04, 0.03, size=n))
    k = min(n_good, n)
    idx = rng.choice(n, size=k, replace=False)
    dislocation[idx] = rng.uniform(1.5, 3.5, size=k)
    obi[idx] = rng.uniform(0.4, 1.0, size=k)
    bid_ask[idx] = rng.uniform(0.005, 0.02, size=k)
    depth[idx] = rng.uniform(25000.0, 80000.0, size=k)
    mdd[idx] = rng.uniform(0.0, 0.01, size=k)
    is_good = np.zeros(n, dtype=bool)
    is_good[idx] = True
    return dislocation, obi, bid_ask, depth, mdd, is_good


def load_csv(path: Path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV not found: {path}")
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    if data.size == 0:
        raise ValueError("CSV is empty")
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] < 6:
        raise ValueError(f"CSV needs >=6 columns; got {data.shape[1]}")
    if not np.isfinite(data[:, :6]).all():
        raise ValueError("CSV has NaN/Inf in required columns")
    a, b, hist = data[:, 1], data[:, 2], data[:, 3]
    spread = np.maximum(data[:, 4], 1e-8)
    depth = np.maximum(data[:, 5], 1e-8)
    dislocation = np.abs((a - b) - hist)
    obi = data[:, 6] if data.shape[1] > 6 else np.zeros(len(data))
    mdd = data[:, 7] if data.shape[1] > 7 else np.zeros(len(data))
    return dislocation, obi, spread, depth, mdd


def map_objectives(profile, dislocation, obi, spread, depth, mdd):
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose from {PROFILES}")
    liq_cost = _norm(spread / (depth + 1e-8))
    risk = _norm(np.maximum(mdd, 0.0))
    if profile == "pairs":
        obj0 = 0.55 * _norm(1.0 / (dislocation + 1e-5)) + 0.45 * _norm(
            (1.0 - np.clip(obi, -1, 1)) * 0.5
        )
        obj1 = 0.55 * liq_cost + 0.45 * risk
    elif profile == "liquidity":
        obj0 = 0.30 * _norm(1.0 / (dislocation + 1e-5)) + 0.70 * liq_cost
        obj1 = 0.40 * risk + 0.60 * _norm(spread)
    elif profile == "stress":
        obj0 = 0.40 * _norm(1.0 / (dislocation + 1e-5)) + 0.60 * risk
        obj1 = 0.50 * liq_cost + 0.50 * _norm(np.abs(obi))
    else:  # micro
        micro_pressure = _norm(np.abs(obi) * dislocation)
        obj0 = 0.50 * micro_pressure + 0.50 * _norm(1.0 / (dislocation + 1e-5))
        obj1 = 0.70 * liq_cost + 0.30 * risk
    X = np.ascontiguousarray(np.column_stack([obj0, obj1]), dtype=np.float64)
    if not np.isfinite(X).all():
        raise ValueError("mapped objectives contain NaN/Inf")
    return X


def compile_finance_matrix(
    out_dir, n=4096, seed=42, n_good=48, profile="pairs", csv=None
):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if csv is not None:
        dislocation, obi, spread, depth, mdd = load_csv(csv)
        is_good, source = None, str(csv)
    else:
        dislocation, obi, spread, depth, mdd, is_good = synthetic_market(n, seed, n_good)
        source = f"synthetic_seed={seed}"
    X = map_objectives(profile, dislocation, obi, spread, depth, mdd)
    X.tofile(out_dir / "matrix.bin")
    meta = {
        "ok": True,
        "adapter_version": ADAPTER_VERSION,
        "domain": "finance",
        "profile": profile,
        "n": int(X.shape[0]),
        "m": 2,
        "source": source,
        "profiles": list(PROFILES),
        "promote_ready": False,
        "non_claims": [
            "Not a trading signal or alpha model",
            "Not an order router",
            "Structural sieve mapping only",
        ],
    }
    if is_good is not None:
        meta["n_good_planted"] = int(is_good.sum())
        np.save(out_dir / "is_good.npy", is_good)
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Finance adapter {ADAPTER_VERSION}")
    ap.add_argument("--input", default=None)
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--n", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-good", type=int, default=48)
    ap.add_argument("--profile", default="pairs", choices=PROFILES)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        if args.n < 1 or args.n > 5_000_000:
            raise ValueError(f"n out of range: {args.n}")
        meta = compile_finance_matrix(
            Path(args.out_dir),
            n=args.n,
            seed=args.seed,
            n_good=args.n_good,
            profile=args.profile,
            csv=Path(args.input) if args.input else None,
        )
        if args.json:
            print(json.dumps(meta))
        else:
            print(
                f"[finance] {ADAPTER_VERSION} profile={meta['profile']} "
                f"n={meta['n']} promote_ready=false"
            )
        return 0
    except Exception as e:
        err = {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "adapter_version": ADAPTER_VERSION,
        }
        print(
            json.dumps(err) if args.json else f"[finance] ERROR: {err['error']}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
