#!/usr/bin/env python3
"""Order-book impact depth estimator (research). Not a matching engine. promote_ready=false."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

VERSION = "0.1.5.1"


def synthetic_book(n_levels: int, seed: int, side: str = "ask"):
    rng = np.random.default_rng(seed)
    if side == "ask":
        prices = 100.0 + np.cumsum(rng.uniform(0.01, 0.05, size=n_levels))
    else:
        prices = 100.0 - np.cumsum(rng.uniform(0.01, 0.05, size=n_levels))
    sizes = rng.integers(100, 5000, size=n_levels).astype(np.float64)
    return prices.astype(np.float64), sizes


def impact_walk(prices: np.ndarray, sizes: np.ndarray, order_size: float):
    remaining = float(order_size)
    filled = 0.0
    notional = 0.0
    levels_used = 0
    for p, s in zip(prices, sizes):
        if remaining <= 0:
            break
        take = min(remaining, s)
        filled += take
        notional += take * p
        remaining -= take
        levels_used += 1
    vwap = notional / filled if filled > 0 else float("nan")
    best = float(prices[0]) if len(prices) else float("nan")
    if len(prices) and prices[-1] > prices[0]:
        slippage_bps = (vwap - best) / best * 1e4 if best and filled > 0 else float("nan")
    else:
        slippage_bps = (best - vwap) / best * 1e4 if best and filled > 0 else float("nan")
    return {
        "order_size": order_size,
        "filled": filled,
        "unfilled": max(0.0, remaining),
        "levels_used": levels_used,
        "vwap": vwap,
        "best": best,
        "slippage_bps": slippage_bps,
        "fill_ratio": filled / order_size if order_size > 0 else 0.0,
    }


def fragile_level_matrix(prices: np.ndarray, sizes: np.ndarray) -> np.ndarray:
    best = prices[0]
    dist = np.abs(prices - best)
    thin = 1.0 / (sizes + 1e-9)

    def norm(x):
        lo, hi = float(x.min()), float(x.max())
        return np.zeros_like(x) if hi - lo < 1e-15 else (x - lo) / (hi - lo)

    return np.ascontiguousarray(np.column_stack([norm(dist), norm(thin)]), dtype=np.float64)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-levels", type=int, default=200)
    ap.add_argument("--order-size", type=float, default=5000)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--side", default="ask", choices=("ask", "bid"))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    prices, sizes = synthetic_book(args.n_levels, args.seed, side=args.side)
    order = np.argsort(prices) if args.side == "ask" else np.argsort(-prices)
    prices, sizes = prices[order], sizes[order]
    summary = impact_walk(prices, sizes, args.order_size)
    summary.update(
        {
            "version": VERSION,
            "side": args.side,
            "n_levels": args.n_levels,
            "promote_ready": False,
            "scope": "structural impact walk only; not a matching engine",
        }
    )

    if args.out_dir:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        X = fragile_level_matrix(prices, sizes)
        X.tofile(out / "matrix.bin")
        summary["matrix_n"] = int(X.shape[0])

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"[orderbook_impact] {VERSION} side={args.side} "
            f"levels_used={summary['levels_used']} fill={summary['fill_ratio']:.3f} "
            f"slip_bps={summary['slippage_bps']:.2f} promote_ready=false"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
