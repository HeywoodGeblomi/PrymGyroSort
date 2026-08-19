#!/usr/bin/env python3
"""Tail-shock stress on research HRP weights. Synthetic returns. promote_ready=false."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

VERSION = "0.1.5.1-research"


def _load_tiers(path: Path) -> dict:
    t = json.loads(path.read_text())
    if not t.get("ok"):
        raise ValueError("tiers.json not ok")
    if t.get("circuit_breaker", {}).get("tripped"):
        raise RuntimeError(f"breaker tripped: {t['circuit_breaker'].get('reasons')}")
    if not t.get("tier1_indices"):
        raise RuntimeError("empty tier1")
    return t


def _corr_distance(corr: np.ndarray) -> np.ndarray:
    d = np.sqrt(0.5 * (1.0 - corr))
    np.fill_diagonal(d, 0.0)
    return d


def _quasi_diag(link: np.ndarray) -> list[int]:
    link = np.asarray(link, dtype=float)
    n = link.shape[0] + 1

    def leaves(i):
        if i < n:
            return [int(i)]
        return leaves(int(link[i - n, 0])) + leaves(int(link[i - n, 1]))

    return leaves(2 * n - 2)


def _cluster_var(cov: np.ndarray, idx: list[int]) -> float:
    sub = cov[np.ix_(idx, idx)]
    w = np.ones(len(idx)) / len(idx)
    return float(w @ sub @ w)


def hrp_weights(cov: np.ndarray) -> np.ndarray:
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform

    n = cov.shape[0]
    if n == 1:
        return np.array([1.0])
    std = np.sqrt(np.clip(np.diag(cov), 1e-18, None))
    corr = cov / np.outer(std, std)
    corr = np.clip(corr, -1.0, 1.0)
    condensed = squareform(_corr_distance(corr), checks=False)
    link = linkage(condensed, method="single")
    order = _quasi_diag(link)
    w = np.ones(n)
    clusters = [order]
    while clusters:
        new = []
        for cl in clusters:
            if len(cl) <= 1:
                continue
            mid = len(cl) // 2
            left, right = cl[:mid], cl[mid:]
            vl, vr = _cluster_var(cov, left), _cluster_var(cov, right)
            a = 1.0 - vl / (vl + vr + 1e-18)
            for i in left:
                w[i] *= a
            for i in right:
                w[i] *= 1.0 - a
            new += [left, right]
        clusters = [c for c in new if len(c) > 1]
    return w / w.sum()


def synth_returns(n_assets: int, T: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    k = 3
    F = rng.normal(0, 0.01, size=(T, k))
    B = rng.normal(0, 1.0, size=(n_assets, k))
    eps = rng.normal(0, 0.005, size=(T, n_assets))
    return F @ B.T + eps


def inject_tail(R: np.ndarray, tier1: list[int], severity: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = R.copy()
    T, _ = out.shape
    n_shock_days = max(1, T // 20)
    days = rng.choice(T, size=n_shock_days, replace=False)
    victims = list(tier1)
    rng.shuffle(victims)
    victims = victims[: max(1, len(victims) // 2)]
    for d in days:
        out[d, victims] -= severity * (0.05 + rng.random(len(victims)) * 0.10)
    out[:, victims] *= 1.0 + 0.5 * severity
    return out


def metrics(w: np.ndarray) -> dict:
    hhi = float(np.sum(w * w))
    return {
        "max_weight": float(w.max()),
        "min_weight": float(w.min()),
        "hhi": hhi,
        "eff_n": float(1.0 / hhi) if hhi > 0 else 0.0,
        "argmax": int(w.argmax()),
    }


def turnover(w0: np.ndarray, w1: np.ndarray) -> float:
    return float(0.5 * np.sum(np.abs(w0 - w1)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="work/tiers.json")
    ap.add_argument("--T", type=int, default=252)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--severities", default="0.5,1.0,2.0,3.0")
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        tiers = _load_tiers(Path(args.tiers))
        tier1 = tiers["tier1_indices"]
        n = int(tiers["n"])
        R0 = synth_returns(n, args.T, args.seed)
        cov0 = np.atleast_2d(np.cov(R0[:, tier1], rowvar=False)) + np.eye(len(tier1)) * 1e-8
        w0 = hrp_weights(cov0)
        base = {"weights": w0.tolist(), **metrics(w0), "tier1": tier1}
        rows = []
        for s in [float(x) for x in args.severities.split(",")]:
            Rs = inject_tail(R0, tier1, s, seed=args.seed + int(10 * s))
            cov = np.atleast_2d(np.cov(Rs[:, tier1], rowvar=False)) + np.eye(len(tier1)) * 1e-8
            w = hrp_weights(cov)
            m = metrics(w)
            rows.append(
                {
                    "severity": s,
                    **m,
                    "turnover_vs_base": turnover(w0, w),
                    "top_name_changed": m["argmax"] != base["argmax"],
                    "weights": w.tolist(),
                }
            )
        out = {
            "ok": True,
            "version": VERSION,
            "promote_ready": False,
            "scope": "synthetic tail-shock research only",
            "T": args.T,
            "tier1_size": len(tier1),
            "baseline": base,
            "shocks": rows,
            "non_claims": [
                "Synthetic returns — not market data",
                "Not a risk model validation",
                "Research stress of HRP-on-tier1 only",
            ],
        }
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "hrp_tail_stress.json").write_text(json.dumps(out, indent=2))
        if args.json:
            print(json.dumps(out))
        else:
            print(f"[hrp_tail_stress] {VERSION} tier1={len(tier1)} T={args.T}")
            print(
                f"  baseline max_w={base['max_weight']:.3f} HHI={base['hhi']:.3f} eff_n={base['eff_n']:.2f}"
            )
            for r in rows:
                print(
                    f"  sev={r['severity']:.1f}  max_w={r['max_weight']:.3f}  "
                    f"HHI={r['hhi']:.3f}  turn={r['turnover_vs_base']:.3f}  "
                    f"top_chg={r['top_name_changed']}"
                )
            print(f"  → {out_dir / 'hrp_tail_stress.json'}  promote_ready=false")
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
