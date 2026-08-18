#!/usr/bin/env python3
"""
PrymGyroSort — Finance Protocol Adapter (v0.1.3)

Maps statistical-arbitrage / pair-filter features into matrix.bin
for the frozen GyroRank kernel.

Objectives (lower = better):
  obj0 = 1 / (|spread - historical_mean| + eps)   # large dislocation preferred
  obj1 = bid_ask_spread / (book_depth + eps)      # low execution risk preferred

Honesty: execution sieve only. No alpha / profitability claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

ADAPTER_VERSION = "0.1.3"


def synthetic_market(n: int, seed: int, n_good: int):
    rng = np.random.default_rng(seed)
    dislocation = rng.exponential(scale=0.35, size=n)
    bid_ask = rng.uniform(0.01, 0.30, size=n)
    depth = rng.uniform(800.0, 40_000.0, size=n)
    n_good = min(n_good, n)
    idx = rng.choice(n, size=n_good, replace=False)
    dislocation[idx] = rng.uniform(1.5, 3.5, size=n_good)
    bid_ask[idx] = rng.uniform(0.005, 0.02, size=n_good)
    depth[idx] = rng.uniform(25_000.0, 80_000.0, size=n_good)
    is_good = np.zeros(n, dtype=bool)
    is_good[idx] = True
    return dislocation, bid_ask, depth, is_good


def load_csv(path: Path):
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] < 6:
        raise SystemExit(
            f"[finance] CSV needs ≥6 columns "
            f"(timestamp,a,b,mean,spread,depth); got {data.shape[1]}"
        )
    a = data[:, 1].astype(np.float64)
    b = data[:, 2].astype(np.float64)
    mean = data[:, 3].astype(np.float64)
    bid_ask = data[:, 4].astype(np.float64)
    depth = data[:, 5].astype(np.float64)
    dislocation = np.abs((a - b) - mean)
    return dislocation, bid_ask, depth, None


def map_objectives(dislocation, bid_ask, depth, normalize: bool = True):
    obj0 = 1.0 / (dislocation + 1e-5)
    obj1 = bid_ask / (depth + 1e-5)
    if normalize:
        def _n(x):
            lo, hi = float(x.min()), float(x.max())
            if hi - lo < 1e-15:
                return np.zeros_like(x)
            return (x - lo) / (hi - lo)
        obj0, obj1 = _n(obj0), _n(obj1)
    return np.column_stack([obj0, obj1]).astype(np.float64)


def compile_finance_matrix(input_path, out_dir: Path, n: int, seed: int, n_good: int, normalize: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    if input_path is not None and Path(input_path).exists():
        print(f"[*] Finance adapter: loading {input_path}")
        dislocation, bid_ask, depth, is_good = load_csv(Path(input_path))
        source = "csv"
    else:
        if input_path is not None:
            print(f"[!] {input_path} not found — synthetic bootstrap", file=sys.stderr)
        else:
            print("[*] Finance adapter: synthetic bootstrap")
        dislocation, bid_ask, depth, is_good = synthetic_market(n, seed, n_good)
        source = "synthetic"

    matrix = map_objectives(dislocation, bid_ask, depth, normalize=normalize)
    n_rows = matrix.shape[0]
    matrix.tofile(out_dir / "matrix.bin")
    if is_good is not None:
        np.save(out_dir / "is_good.npy", is_good)

    meta = {
        "n": n_rows,
        "m": 2,
        "domain": "finance_pair_arbitrage",
        "adapter_version": ADAPTER_VERSION,
        "source": source,
        "seed": seed if source == "synthetic" else None,
        "n_good": int(is_good.sum()) if is_good is not None else None,
        "objectives": {
            "obj0": "pricing_residual_proxy = 1/(|spread-mean|+eps)",
            "obj1": "liquidity_risk_proxy = bid_ask_spread/(book_depth+eps)",
        },
        "normalize": normalize,
        "promote_ready": False,
        "scope": "execution sieve only; no alpha / profitability claim",
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[+] Finance matrix locked: {out_dir / 'matrix.bin'} "
          f"(N={n_rows} M=2 source={source} promote_ready=false)")
    return meta


def main() -> int:
    p = argparse.ArgumentParser(description="PrymGyroSort finance protocol adapter")
    p.add_argument("--input", default=None, help="CSV market feed (optional)")
    p.add_argument("--out-dir", default="work")
    p.add_argument("--n", type=int, default=4096)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-good", type=int, default=48)
    p.add_argument("--no-normalize", action="store_true")
    args = p.parse_args()
    compile_finance_matrix(
        input_path=Path(args.input) if args.input else None,
        out_dir=Path(args.out_dir),
        n=args.n, seed=args.seed, n_good=args.n_good,
        normalize=not args.no_normalize,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
