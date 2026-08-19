#!/usr/bin/env python3
"""Research-only HRP on sieve tier-1. promote_ready=false — not a live allocator."""
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
        raise RuntimeError(f"refusing HRP: breaker tripped {t['circuit_breaker'].get('reasons')}")
    if not t.get("tier1_indices"):
        raise RuntimeError("tier1 empty — nothing to allocate")
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
        a = int(link[i - n, 0])
        b = int(link[i - n, 1])
        return leaves(a) + leaves(b)

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
    dist = _corr_distance(corr)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="single")
    order = _quasi_diag(link)
    w = np.ones(n)
    clusters = [order]
    while clusters:
        new_clusters = []
        for cl in clusters:
            if len(cl) <= 1:
                continue
            split = len(cl) // 2
            left, right = cl[:split], cl[split:]
            var_l = _cluster_var(cov, left)
            var_r = _cluster_var(cov, right)
            alpha = 1.0 - var_l / (var_l + var_r + 1e-18)
            for i in left:
                w[i] *= alpha
            for i in right:
                w[i] *= 1.0 - alpha
            new_clusters += [left, right]
        clusters = [c for c in new_clusters if len(c) > 1]
    return w / w.sum()


def main() -> int:
    ap = argparse.ArgumentParser(description="Research HRP on tier-1")
    ap.add_argument("--tiers", default="work/tiers.json")
    ap.add_argument("--returns", default=None, help="optional (T,N) float64 .npy")
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        tiers = _load_tiers(Path(args.tiers))
        tier1 = tiers["tier1_indices"]
        n_full = int(tiers["n"])
        if args.returns:
            R = np.load(args.returns)
            if R.ndim != 2 or R.shape[1] != n_full:
                raise ValueError(f"returns shape {R.shape} incompatible with n={n_full}")
            sub = R[:, tier1]
            cov = np.atleast_2d(np.cov(sub, rowvar=False))
            cov = cov + np.eye(cov.shape[0]) * 1e-8
            w = hrp_weights(cov)
            method = "hrp"
        else:
            w = np.ones(len(tier1)) / len(tier1)
            method = "equal_weight_tier1_no_returns"
        out = {
            "ok": True,
            "version": VERSION,
            "method": method,
            "tier1_size": len(tier1),
            "tier1_indices": tier1,
            "weights": w.tolist(),
            "weight_sum": float(w.sum()),
            "promote_ready": False,
            "scope": "research notebook path only — not a live allocator",
            "non_claims": [
                "Not investment advice",
                "Not production portfolio construction",
                "Requires unbroken tiers.json (circuit breaker green)",
            ],
        }
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "hrp_research.json").write_text(json.dumps(out, indent=2))
        if args.json:
            print(json.dumps(out))
        else:
            print(
                f"[hrp_research] {VERSION} method={method} tier1={len(tier1)} "
                f"w_sum={w.sum():.4f} promote_ready=false → {out_dir / 'hrp_research.json'}"
            )
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
