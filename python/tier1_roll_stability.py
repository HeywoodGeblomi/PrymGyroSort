#!/usr/bin/env python3
"""Rolling tier-1 membership stability under feature drift. promote_ready=false."""
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

try:
    from prym_gyro import rank
except Exception as e:  # pragma: no cover
    print(json.dumps({"ok": False, "error": f"native_binding: {e}"}), file=sys.stderr)
    raise SystemExit(3)


def tier1_from_matrix(X: np.ndarray, q: float = 0.25) -> list[int]:
    X = np.ascontiguousarray(X, dtype=np.float64)
    if q is not None:
        keep = filter_quantile(X, q)
        idx = np.flatnonzero(keep)
        ranks = np.full(X.shape[0], 10**9, dtype=np.int32)
        if idx.size:
            ranks[idx] = rank(np.ascontiguousarray(X[idx]))
    else:
        ranks = rank(X)
    return np.flatnonzero(ranks == 1).tolist()


def jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Rolling tier-1 stability")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--windows", type=int, default=20)
    ap.add_argument("--seed0", type=int, default=7)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--risk-mode", default="vol_mdd")
    ap.add_argument("--n-good", type=int, default=24)
    ap.add_argument("--drift", type=float, default=0.05, help="per-window relative feature drift")
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        from protocol_portfolio import synthetic_portfolios, map_objectives

        ret, vol, mdd, te, planted = synthetic_portfolios(args.n, args.seed0, args.n_good)
        rng = np.random.default_rng(args.seed0 + 999)

        tier_sets: list[set[int]] = []
        sizes = []
        for w in range(args.windows):
            if w > 0:
                ret = ret + rng.normal(0, args.drift * 0.02, size=ret.shape)
                vol = np.clip(vol * (1.0 + rng.normal(0, args.drift, size=vol.shape)), 0.01, None)
                mdd = np.clip(mdd * (1.0 + rng.normal(0, args.drift, size=mdd.shape)), 0.01, None)
                te = np.clip(te * (1.0 + rng.normal(0, args.drift * 0.5, size=te.shape)), 0.005, None)
            X = map_objectives(ret, vol, mdd, te, risk_mode=args.risk_mode)
            t1 = set(tier1_from_matrix(X, q=args.q))
            tier_sets.append(t1)
            sizes.append(len(t1))

        j_cons = [jaccard(tier_sets[i], tier_sets[i + 1]) for i in range(len(tier_sets) - 1)]
        origin = tier_sets[0]
        if origin:
            surv = {int(i): float(np.mean([i in s for s in tier_sets])) for i in origin}
            mean_surv = float(np.mean(list(surv.values())))
        else:
            surv, mean_surv = {}, 0.0
        origin_frac = [len(origin & s) / max(1, len(origin)) for s in tier_sets]

        out = {
            "ok": True,
            "version": VERSION,
            "promote_ready": False,
            "n": args.n,
            "windows": args.windows,
            "seed0": args.seed0,
            "q": args.q,
            "risk_mode": args.risk_mode,
            "drift": args.drift,
            "tier1_sizes": sizes,
            "tier1_size_mean": float(np.mean(sizes)),
            "tier1_size_std": float(np.std(sizes)),
            "jaccard_consecutive": j_cons,
            "jaccard_mean": float(np.mean(j_cons)) if j_cons else 0.0,
            "jaccard_min": float(np.min(j_cons)) if j_cons else 0.0,
            "origin_tier1": sorted(origin),
            "origin_name_survival": surv,
            "mean_origin_name_survival": mean_surv,
            "origin_set_frac_by_window": origin_frac,
            "scope": "synthetic drifted portfolio features — structural membership only",
            "non_claims": [
                "Not a backtest of returns",
                "Not proof of live portfolio stability",
                "Drifted synthetic features; not calendar bars",
            ],
        }
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "tier1_roll_stability.json").write_text(json.dumps(out, indent=2))

        if args.json:
            print(json.dumps(out))
        else:
            print(
                f"[tier1_roll] {VERSION} windows={args.windows} n={args.n} "
                f"size≈{out['tier1_size_mean']:.1f}±{out['tier1_size_std']:.1f}"
            )
            print(
                f"  J@tier1 mean={out['jaccard_mean']:.3f} min={out['jaccard_min']:.3f}  "
                f"origin_name_surv={mean_surv:.3f}"
            )
            print(f"  → {out_dir / 'tier1_roll_stability.json'}  promote_ready=false")
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
