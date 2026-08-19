#!/usr/bin/env python3
"""Tier-2 catch of Tier-1 dropouts under feature drift. promote_ready=false."""
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


def ranks_full(X: np.ndarray, q: float = 0.25) -> np.ndarray:
    X = np.ascontiguousarray(X, dtype=np.float64)
    ranks = np.full(X.shape[0], 10**9, dtype=np.int32)
    if q is not None:
        keep = filter_quantile(X, q)
        idx = np.flatnonzero(keep)
        if idx.size:
            ranks[idx] = rank(np.ascontiguousarray(X[idx]))
    else:
        ranks[:] = rank(X)
    return ranks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--windows", type=int, default=20)
    ap.add_argument("--seed0", type=int, default=7)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--drift", type=float, default=0.05)
    ap.add_argument("--risk-mode", default="vol_mdd")
    ap.add_argument("--n-good", type=int, default=24)
    ap.add_argument("--k", type=int, default=3, help="catch band rank_2..k")
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        from protocol_portfolio import synthetic_portfolios, map_objectives

        ret, vol, mdd, te, _ = synthetic_portfolios(args.n, args.seed0, args.n_good)
        rng = np.random.default_rng(args.seed0 + 999)
        rank_hist = []
        for w in range(args.windows):
            if w > 0:
                ret = ret + rng.normal(0, args.drift * 0.02, size=ret.shape)
                vol = np.clip(vol * (1.0 + rng.normal(0, args.drift, size=vol.shape)), 0.01, None)
                mdd = np.clip(mdd * (1.0 + rng.normal(0, args.drift, size=mdd.shape)), 0.01, None)
                te = np.clip(te * (1.0 + rng.normal(0, args.drift * 0.5, size=te.shape)), 0.005, None)
            X = map_objectives(ret, vol, mdd, te, risk_mode=args.risk_mode)
            rank_hist.append(ranks_full(X, q=args.q))

        dropouts = caught_r2 = caught_band = lost = 0
        details = []
        for w in range(len(rank_hist) - 1):
            r0, r1 = rank_hist[w], rank_hist[w + 1]
            t1_prev = set(np.flatnonzero(r0 == 1).tolist())
            for i in t1_prev:
                if r1[i] == 1:
                    continue
                dropouts += 1
                nr = int(r1[i])
                if nr == 2:
                    caught_r2 += 1
                    caught_band += 1
                    tag = "rank_2"
                elif 2 <= nr <= args.k:
                    caught_band += 1
                    tag = f"rank_{nr}"
                else:
                    lost += 1
                    tag = "lost" if nr >= 10**8 else f"rank_{nr}"
                details.append({"window": w, "name": int(i), "new_rank": nr if nr < 10**8 else None, "tag": tag})

        out = {
            "ok": True,
            "version": VERSION,
            "promote_ready": False,
            "windows": args.windows,
            "drift": args.drift,
            "k": args.k,
            "dropouts": dropouts,
            "caught_rank2": caught_r2,
            "caught_band_2_to_k": caught_band,
            "lost": lost,
            "catch_rate_rank2": (caught_r2 / dropouts) if dropouts else 1.0,
            "catch_rate_band": (caught_band / dropouts) if dropouts else 1.0,
            "lost_rate": (lost / dropouts) if dropouts else 0.0,
            "details_head": details[:50],
            "scope": "synthetic drift — structural tier migration only",
            "non_claims": ["Not a trading signal", "Not proof of live risk tiering"],
        }
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "tier2_dropout_catch.json").write_text(json.dumps(out, indent=2))
        if args.json:
            print(json.dumps(out))
        else:
            print(
                f"[tier2_catch] {VERSION} windows={args.windows} drift={args.drift} "
                f"dropouts={dropouts} r2={caught_r2} band={caught_band} lost={lost}"
            )
            print(
                f"  catch@r2={out['catch_rate_rank2']:.3f}  catch@2..{args.k}={out['catch_rate_band']:.3f}  "
                f"lost={out['lost_rate']:.3f}"
            )
            print(f"  → {out_dir / 'tier2_dropout_catch.json'}  promote_ready=false")
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
