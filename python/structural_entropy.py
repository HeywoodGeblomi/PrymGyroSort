#!/usr/bin/env python3
"""Structural entropy + spread diagnostic for feature homogenization. promote_ready=false."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

VERSION = "0.1.5.1-research"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def normalized_eigen_entropy(matrix: np.ndarray) -> float:
    X = np.asarray(matrix, dtype=np.float64)
    if X.ndim != 2 or X.shape[0] < 2:
        return float("nan")
    mu = X.mean(axis=0, keepdims=True)
    sd = X.std(axis=0, keepdims=True)
    sd = np.where(sd < 1e-15, 1.0, sd)
    Z = (X - mu) / sd
    G = (Z.T @ Z) / max(1, Z.shape[0] - 1)
    ev = np.linalg.eigvalsh(0.5 * (G + G.T))
    ev = np.clip(ev, 1e-15, None)
    p = ev / ev.sum()
    H = float(-np.sum(p * np.log2(p)))
    return H / np.log2(len(ev)) if len(ev) > 1 else 0.0


def asset_corr_entropy(matrix: np.ndarray, max_n: int = 128) -> float:
    X = np.asarray(matrix, dtype=np.float64)
    n = X.shape[0]
    if n < 4:
        return float("nan")
    rng = np.random.default_rng(0)
    idx = np.arange(n) if n <= max_n else rng.choice(n, size=max_n, replace=False)
    Z = X[idx]
    Z = (Z - Z.mean(axis=0)) / np.maximum(Z.std(axis=0), 1e-15)
    C = Z @ Z.T / Z.shape[1]
    ev = np.linalg.eigvalsh(0.5 * (C + C.T))
    ev = np.clip(ev, 1e-15, None)
    k = min(32, len(ev))
    top = np.sort(ev)[-k:]
    p = top / top.sum()
    H = float(-np.sum(p * np.log2(p)))
    return H / np.log2(k)


def collapse_matrix(X: np.ndarray, rho: float, rng: np.random.Generator) -> np.ndarray:
    mu = X.mean(axis=0, keepdims=True)
    Y = (1.0 - rho) * X + rho * np.repeat(mu, X.shape[0], axis=0)
    Y = Y + rng.normal(0, 1e-6 * (1.0 + 10 * rho), size=Y.shape)
    return np.ascontiguousarray(Y, dtype=np.float64)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=7)
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
        for rho in [float(x) for x in args.rhos.split(",")]:
            X = collapse_matrix(X0, rho, rng)
            G = np.cov(X, rowvar=False)
            ev = np.clip(np.linalg.eigvalsh(0.5 * (G + G.T)), 1e-15, None)
            cond = float(ev.max() / ev.min())
            rows.append(
                {
                    "rho": rho,
                    "feature_gram_entropy": normalized_eigen_entropy(X),
                    "asset_corr_entropy": asset_corr_entropy(X),
                    "feature_spread": float(X.std()),
                    "feature_gram_condition": cond,
                    "col_corr": float(np.corrcoef(X[:, 0], X[:, 1])[0, 1]),
                }
            )
        out = {
            "ok": True,
            "version": VERSION,
            "promote_ready": False,
            "n": args.n,
            "rows": rows,
            "primary_signal": "feature_spread (monotonic collapse under mean-blend)",
            "note": (
                "Diagnostic only. Production circuit breaker is size-based and "
                "does not consume this entropy/spread signal. For M=2, feature Gram "
                "entropy stays near 1; spread is the reliable flattening metric."
            ),
            "non_claims": [
                "Not a production kill-switch",
                "Not wired into tier_export breaker",
            ],
        }
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "structural_entropy.json").write_text(json.dumps(out, indent=2))
        if args.json:
            print(json.dumps(out))
        else:
            print(f"[struct_entropy] {VERSION} n={args.n}")
            for r in rows:
                print(
                    f"  rho={r['rho']:.2f}  spread={r['feature_spread']:.4f}  "
                    f"cond={r['feature_gram_condition']:.2f}  "
                    f"feat_H={r['feature_gram_entropy']:.4f}  "
                    f"asset_H={r['asset_corr_entropy']:.4f}"
                )
            print(f"  → {out_dir / 'structural_entropy.json'}  promote_ready=false")
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
