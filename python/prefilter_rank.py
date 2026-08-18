#!/usr/bin/env python3
"""Coarse pre-filter + ensemble helpers. promote_ready=false."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

from prym_gyro import rank  # noqa: E402


def make_ensemble(n: int, seed: int, n_good: int = 48):
    """Return (X, is_good) with X shape (N, 2)."""
    rng = np.random.default_rng(seed)
    obj0 = rng.random(n)
    obj1 = rng.random(n)
    k = min(n_good, n)
    idx = rng.choice(n, size=k, replace=False)
    obj0[idx] = rng.uniform(0.0, 0.08, size=k)
    obj1[idx] = rng.uniform(0.0, 0.08, size=k)
    X = np.ascontiguousarray(np.column_stack([obj0, obj1]), dtype=np.float64)
    is_good = np.zeros(n, dtype=bool)
    is_good[idx] = True
    return X, is_good


def filter_quantile(X: np.ndarray, q: float) -> np.ndarray:
    """Keep rows in bottom-q fraction on obj0 OR obj1 (lower-better)."""
    if X.ndim != 2 or X.shape[1] < 2:
        raise ValueError(
            f"filter_quantile expects (N, >=2) matrix, got shape {getattr(X, 'shape', None)}"
        )
    n = X.shape[0]
    k = max(1, int(np.ceil(q * n)))
    t0 = np.partition(X[:, 0], k - 1)[k - 1]
    t1 = np.partition(X[:, 1], k - 1)[k - 1]
    return (X[:, 0] <= t0) | (X[:, 1] <= t1)


def top_frac_indices(ranks: np.ndarray, frac: float) -> np.ndarray:
    k = max(1, int(frac * ranks.shape[0]))
    return np.argsort(ranks, kind="stable")[:k]


def rank1_indices(ranks: np.ndarray) -> np.ndarray:
    return np.flatnonzero(ranks == ranks.min())


def recall(true_idx: np.ndarray, pred_idx: np.ndarray) -> float:
    if true_idx.size == 0:
        return 1.0
    return float(np.isin(true_idx, pred_idx).mean())
