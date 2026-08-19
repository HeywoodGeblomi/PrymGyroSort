#!/usr/bin/env python3
"""Long drift replay of tier-1 membership + feature centroids. promote_ready=false."""
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
except Exception as e:
    print(json.dumps({"ok": False, "error": f"native: {e}"}), file=sys.stderr)
    raise SystemExit(3)


def tier1_and_centroid(X: np.ndarray, q: float = 0.25):
    X = np.ascontiguousarray(X, dtype=np.float64)
    ranks = np.full(X.shape[0], 10**9, dtype=np.int32)
    keep = filter_quantile(X, q)
    idx = np.flatnonzero(keep)
    if idx.size:
        ranks[idx] = rank(np.ascontiguousarray(X[idx]))
    t1 = np.flatnonzero(ranks == 1)
    if t1.size == 0:
        return set(), np.array([np.nan, np.nan])
    return set(t1.tolist()), X[t1].mean(axis=0)


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--windows", type=int, default=60)
    ap.add_argument("--seed0", type=int, default=7)
    ap.add_argument("--drift", type=float, default=0.05)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        from protocol_portfolio import synthetic_portfolios, map_objectives

        ret, vol, mdd, te, _ = synthetic_portfolios(args.n, args.seed0, 24)
        rng = np.random.default_rng(args.seed0 + 999)
        sets, cents, sizes = [], [], []
        for w in range(args.windows):
            if w > 0:
                ret = ret + rng.normal(0, args.drift * 0.02, size=ret.shape)
                vol = np.clip(vol * (1.0 + rng.normal(0, args.drift, size=vol.shape)), 0.01, None)
                mdd = np.clip(mdd * (1.0 + rng.normal(0, args.drift, size=mdd.shape)), 0.01, None)
                te = np.clip(te * (1.0 + rng.normal(0, args.drift * 0.5, size=te.shape)), 0.005, None)
            X = map_objectives(ret, vol, mdd, te, risk_mode="vol_mdd")
            s, c = tier1_and_centroid(X, q=args.q)
            sets.append(s)
            cents.append(c)
            sizes.append(len(s))
        cents = np.asarray(cents, dtype=float)
        j_cons = [jaccard(sets[i], sets[i + 1]) for i in range(len(sets) - 1)]
        speed = [float(np.linalg.norm(cents[i + 1] - cents[i])) for i in range(len(cents) - 1)]
        origin = sets[0]
        mean_surv = (
            float(np.mean([np.mean([i in s for s in sets]) for i in origin])) if origin else 0.0
        )
        out = {
            "ok": True,
            "version": VERSION,
            "promote_ready": False,
            "n": args.n,
            "windows": args.windows,
            "drift": args.drift,
            "tier1_size_mean": float(np.mean(sizes)),
            "tier1_size_std": float(np.std(sizes)),
            "jaccard_mean": float(np.mean(j_cons)) if j_cons else 0.0,
            "jaccard_min": float(np.min(j_cons)) if j_cons else 0.0,
            "origin_name_survival": mean_surv,
            "centroid_path": cents.tolist(),
            "centroid_speed": speed,
            "centroid_speed_mean": float(np.mean(speed)) if speed else 0.0,
            "centroid_speed_max": float(np.max(speed)) if speed else 0.0,
            "centroid_total_path": float(np.sum(speed)) if speed else 0.0,
            "scope": "synthetic feature drift — not a returns backtest",
            "non_claims": ["Not historical market replay", "Not live allocation"],
        }
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "tier_centroid_replay.json").write_text(json.dumps(out, indent=2))
        if args.json:
            print(json.dumps(out))
        else:
            print(
                f"[centroid_replay] {VERSION} windows={args.windows} drift={args.drift} "
                f"size≈{out['tier1_size_mean']:.1f}±{out['tier1_size_std']:.1f}"
            )
            print(
                f"  J@tier1 mean={out['jaccard_mean']:.3f} min={out['jaccard_min']:.3f}  "
                f"origin_surv={mean_surv:.3f}"
            )
            print(
                f"  centroid_speed mean={out['centroid_speed_mean']:.5f} "
                f"max={out['centroid_speed_max']:.5f} path={out['centroid_total_path']:.4f}"
            )
            print(f"  → {out_dir / 'tier_centroid_replay.json'}  promote_ready=false")
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
