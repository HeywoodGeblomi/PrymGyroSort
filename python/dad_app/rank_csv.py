#!/usr/bin/env python3
"""CSV → M=2 matrix → ranks. No Streamlit dependency."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

REQUIRED = ("ticker", "return_score", "risk_score")


def _norm(x: np.ndarray) -> np.ndarray:
    lo, hi = float(np.min(x)), float(np.max(x))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-15:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def load_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. Need {list(REQUIRED)}")
    df = df.dropna(subset=list(REQUIRED)).copy()
    if len(df) < 2:
        raise ValueError("Need at least 2 rows")
    df["return_score"] = pd.to_numeric(df["return_score"], errors="coerce")
    df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce")
    if df[["return_score", "risk_score"]].isna().any().any():
        raise ValueError("scores must be numeric")
    return df


def to_matrix(df: pd.DataFrame) -> np.ndarray:
    obj0 = _norm(-df["return_score"].to_numpy(dtype=np.float64))
    obj1 = _norm(df["risk_score"].to_numpy(dtype=np.float64))
    return np.ascontiguousarray(np.column_stack([obj0, obj1]), dtype=np.float64)


def rank_rows(X: np.ndarray) -> np.ndarray:
    try:
        from prym_gyro import rank

        return rank(X)
    except Exception:
        n = X.shape[0]
        ranks = np.zeros(n, dtype=np.int32)
        remaining = np.ones(n, dtype=bool)
        layer = 1
        while remaining.any():
            idx = np.flatnonzero(remaining)
            front = []
            for i in idx:
                dominated = False
                for j in idx:
                    if i == j:
                        continue
                    if (X[j, 0] <= X[i, 0] and X[j, 1] <= X[i, 1]) and (
                        X[j, 0] < X[i, 0] or X[j, 1] < X[i, 1]
                    ):
                        dominated = True
                        break
                if not dominated:
                    front.append(i)
            if not front:
                ranks[remaining] = layer
                break
            for i in front:
                ranks[i] = layer
                remaining[i] = False
            layer += 1
        return ranks


def rank_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["rank"] = rank_rows(to_matrix(df))
    return out.sort_values(["rank", "ticker"]).reset_index(drop=True)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    out = rank_dataframe(load_csv(args.csv))
    cols = [c for c in ["ticker", "name", "return_score", "risk_score", "rank"] if c in out.columns]
    print(out[cols].to_string(index=False))
