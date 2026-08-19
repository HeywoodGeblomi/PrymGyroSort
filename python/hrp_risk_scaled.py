#!/usr/bin/env python3
"""Risk-scaled HRP on tier-1 vs equal/inv_vol baselines. promote_ready=false."""
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
        raise ValueError("tiers not ok")
    if t.get("circuit_breaker", {}).get("tripped"):
        raise RuntimeError("breaker tripped")
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
    corr = np.clip(cov / np.outer(std, std), -1.0, 1.0)
    link = linkage(squareform(_corr_distance(corr), checks=False), method="single")
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


def synth_returns(n: int, T: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    F = rng.normal(0, 0.01, size=(T, 3))
    B = rng.normal(0, 1.0, size=(n, 3))
    return F @ B.T + rng.normal(0, 0.005, size=(T, n))


def metrics(w: np.ndarray, cov: np.ndarray) -> dict:
    port_var = float(w @ cov @ w)
    hhi = float(np.sum(w * w))
    return {
        "max_weight": float(w.max()),
        "min_weight": float(w.min()),
        "hhi": hhi,
        "eff_n": float(1.0 / hhi) if hhi > 0 else 0.0,
        "port_vol": float(np.sqrt(max(port_var, 0.0))),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="work/tiers.json")
    ap.add_argument("--T", type=int, default=252)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        tiers = _load_tiers(Path(args.tiers))
        tier1 = tiers["tier1_indices"]
        n = int(tiers["n"])
        R = synth_returns(n, args.T, args.seed)
        sub = R[:, tier1]
        cov = np.atleast_2d(np.cov(sub, rowvar=False)) + np.eye(len(tier1)) * 1e-8
        vol = np.sqrt(np.clip(np.diag(cov), 1e-18, None))
        modes = {}
        w = np.ones(len(tier1)) / len(tier1)
        modes["equal"] = {"weights": w.tolist(), **metrics(w, cov)}
        w = (1.0 / vol)
        w = w / w.sum()
        modes["inv_vol"] = {"weights": w.tolist(), **metrics(w, cov)}
        w = hrp_weights(cov)
        modes["hrp"] = {"weights": w.tolist(), **metrics(w, cov)}
        Rs = sub / vol
        cov_s = np.atleast_2d(np.cov(Rs, rowvar=False)) + np.eye(len(tier1)) * 1e-8
        w = hrp_weights(cov_s)
        modes["hrp_vol"] = {"weights": w.tolist(), **metrics(w, cov)}
        out = {
            "ok": True,
            "version": VERSION,
            "promote_ready": False,
            "tier1_size": len(tier1),
            "tier1_indices": tier1,
            "modes": modes,
            "scope": "synthetic returns research comparison only",
            "non_claims": ["Not investment advice", "Not a live allocator"],
        }
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "hrp_risk_scaled.json").write_text(json.dumps(out, indent=2))
        if args.json:
            print(json.dumps(out))
        else:
            print(f"[hrp_risk_scaled] {VERSION} tier1={len(tier1)}")
            for name, m in modes.items():
                print(
                    f"  {name:<8} max_w={m['max_weight']:.3f} HHI={m['hhi']:.3f} "
                    f"eff_n={m['eff_n']:.2f} port_vol={m['port_vol']:.5f}"
                )
            print(f"  → {out_dir / 'hrp_risk_scaled.json'}  promote_ready=false")
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
