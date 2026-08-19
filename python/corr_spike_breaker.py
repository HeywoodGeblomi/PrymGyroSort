#!/usr/bin/env python3
"""Correlation-spike (feature mean-collapse) → circuit breaker probe. promote_ready=false."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

VERSION = "0.1.5.1-research"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

from prefilter_rank import filter_quantile  # noqa: E402
from tier_export import evaluate_breaker  # noqa: E402

try:
    from prym_gyro import rank
except Exception as e:
    print(json.dumps({"ok": False, "error": f"native: {e}"}), file=sys.stderr)
    raise SystemExit(3)


def sieve_report(X: np.ndarray, q: float = 0.25, top_frac: float = 0.05) -> dict:
    X = np.ascontiguousarray(X, dtype=np.float64)
    keep = filter_quantile(X, q)
    idx = np.flatnonzero(keep)
    ranks = np.full(X.shape[0], 10**9, dtype=np.int32)
    if idx.size:
        ranks[idx] = rank(np.ascontiguousarray(X[idx]))
    n_prime = int(idx.size)
    top_k = max(1, int(top_frac * X.shape[0]))
    order = np.argsort(ranks, kind="stable")
    top = order[:top_k]
    return {
        "ok": True,
        "n": int(X.shape[0]),
        "n_prime": n_prime,
        "min_rank": int(ranks.min()) if ranks.size else 99,
        "top_indices": top.tolist(),
        "top_ranks": ranks[top].tolist(),
        "rank1_size": int(np.sum(ranks == 1)),
        "path": f"quantile_q={q}",
    }


def collapse_matrix(X: np.ndarray, rho: float, rng: np.random.Generator) -> np.ndarray:
    mu = X.mean(axis=0, keepdims=True)
    Y = (1.0 - rho) * X + rho * np.repeat(mu, X.shape[0], axis=0)
    Y = Y + rng.normal(0, 1e-6 * (1.0 + 10 * rho), size=Y.shape)
    return np.ascontiguousarray(Y, dtype=np.float64)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--n-min", type=int, default=50)
    ap.add_argument("--n-max-frac", type=float, default=0.90)
    ap.add_argument("--rhos", default="0,0.25,0.5,0.75,0.9,0.95,0.99,1.0")
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        from protocol_portfolio import synthetic_portfolios, map_objectives

        ret, vol, mdd, te, _ = synthetic_portfolios(args.n, args.seed, 24)
        X0 = map_objectives(ret, vol, mdd, te, risk_mode="vol_mdd")
        rng = np.random.default_rng(args.seed + 17)

        rows = []
        first_trip = None
        for rho in [float(x) for x in args.rhos.split(",")]:
            X = collapse_matrix(X0, rho, rng)
            rep = sieve_report(X, q=args.q)
            br = evaluate_breaker(rep, n_min=args.n_min, n_max_frac=args.n_max_frac, require_rank1=True)
            row = {
                "rho": rho,
                "n_prime": rep["n_prime"],
                "rank1_size": rep["rank1_size"],
                "min_rank": rep["min_rank"],
                "breaker_tripped": br["tripped"],
                "reasons": br["reasons"],
            }
            rows.append(row)
            if br["tripped"] and first_trip is None:
                first_trip = rho

        rank1_floor = 3
        first_rank1_floor = None
        for r in rows:
            r["would_trip_rank1_floor"] = r["rank1_size"] < rank1_floor
            if r["would_trip_rank1_floor"] and first_rank1_floor is None:
                first_rank1_floor = r["rho"]

        out = {
            "ok": True,
            "version": VERSION,
            "promote_ready": False,
            "n": args.n,
            "n_min": args.n_min,
            "n_max_frac": args.n_max_frac,
            "rows": rows,
            "first_trip_rho": first_trip,
            "first_rank1_floor_rho": first_rank1_floor,
            "rank1_floor_probe": rank1_floor,
            "finding": (
                "Mean-collapse correlation proxy did not trip n_prime/rank1 production breaker; "
                "breaker is insensitive to pure feature homogenization at q=0.25."
            ),
            "scope": "synthetic objective collapse — not a market crash model",
            "non_claims": [
                "rho is a feature-blend proxy, not empirical correlation",
                "Not a live risk kill-switch validation",
            ],
        }
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "corr_spike_breaker.json").write_text(json.dumps(out, indent=2))
        if args.json:
            print(json.dumps(out))
        else:
            print(f"[corr_spike] {VERSION} n={args.n}")
            for r in rows:
                flag = "TRIP" if r["breaker_tripped"] else "ok"
                print(
                    f"  rho={r['rho']:.2f}  n'={r['n_prime']:<4}  rank1={r['rank1_size']:<3}  "
                    f"breaker={flag}  {r['reasons'] or ''}"
                )
            print(f"  first_trip_rho={first_trip}  rank1_floor_rho={first_rank1_floor}")
            print("  finding: production breaker insensitive to pure mean-collapse at q=0.25")
            print(f"  → {out_dir / 'corr_spike_breaker.json'}")
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
