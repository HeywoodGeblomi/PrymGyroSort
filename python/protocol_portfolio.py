#!/usr/bin/env python3
"""Portfolio multi-objective adapter — structural non-dominated tiers. promote_ready=false."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

VERSION = "0.1.5.1"


def _norm(x: np.ndarray) -> np.ndarray:
    lo, hi = float(np.min(x)), float(np.max(x))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-15:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def synthetic_portfolios(n: int, seed: int, n_good: int = 24):
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.08, 0.12, size=n)
    vol = np.abs(rng.normal(0.15, 0.08, size=n)) + 0.02
    mdd = np.abs(rng.normal(0.12, 0.07, size=n)) + 0.01
    te = np.abs(rng.normal(0.05, 0.03, size=n))
    k = min(n_good, n)
    idx = rng.choice(n, size=k, replace=False)
    ret[idx] = rng.uniform(0.12, 0.25, size=k)
    vol[idx] = rng.uniform(0.04, 0.10, size=k)
    mdd[idx] = rng.uniform(0.02, 0.08, size=k)
    te[idx] = rng.uniform(0.01, 0.03, size=k)
    is_good = np.zeros(n, dtype=bool)
    is_good[idx] = True
    return ret, vol, mdd, te, is_good


def map_objectives(ret, vol, mdd, te, risk_mode: str = "vol_mdd"):
    obj0 = _norm(-ret)
    if risk_mode == "vol":
        obj1 = _norm(vol)
    elif risk_mode == "mdd":
        obj1 = _norm(mdd)
    elif risk_mode == "te":
        obj1 = _norm(te)
    else:
        obj1 = _norm(0.6 * vol + 0.4 * mdd)
    X = np.ascontiguousarray(np.column_stack([obj0, obj1]), dtype=np.float64)
    if not np.isfinite(X).all():
        raise ValueError("non-finite objectives")
    return X


def compile_portfolio_matrix(out_dir: Path, n=500, seed=7, n_good=24, risk_mode="vol_mdd"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ret, vol, mdd, te, is_good = synthetic_portfolios(n, seed, n_good)
    X = map_objectives(ret, vol, mdd, te, risk_mode=risk_mode)
    X.tofile(out_dir / "matrix.bin")
    np.save(out_dir / "is_good.npy", is_good)
    meta = {
        "ok": True,
        "adapter": "protocol_portfolio",
        "version": VERSION,
        "n": int(n),
        "m": 2,
        "risk_mode": risk_mode,
        "objectives": {
            "obj0": "-return (normalized, lower better)",
            "obj1": f"risk:{risk_mode} (lower better)",
        },
        "n_good_planted": int(is_good.sum()),
        "promote_ready": False,
        "non_claims": [
            "Not Markowitz optimizer",
            "Not a trading signal",
            "Structural non-dominated tier ranking only",
        ],
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Portfolio tier adapter")
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n-good", type=int, default=24)
    ap.add_argument("--risk-mode", default="vol_mdd", choices=("vol", "mdd", "te", "vol_mdd"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        meta = compile_portfolio_matrix(
            Path(args.out_dir), n=args.n, seed=args.seed, n_good=args.n_good, risk_mode=args.risk_mode
        )
        if args.json:
            print(json.dumps(meta))
        else:
            print(
                f"[portfolio] {VERSION} n={meta['n']} risk_mode={meta['risk_mode']} "
                f"planted={meta['n_good_planted']} promote_ready=false"
            )
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
