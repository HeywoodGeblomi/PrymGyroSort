"""
GYR-SIEVE-001 Track 3 — Geometry as prefilter, not ranker.

Named prefilter: or_quantile
  Keep rows in the bottom-q fraction on obj0 OR obj1 (lower-is-better).
  Output: boolean mask (or compacted matrix). No ranks.

Kill-switch: off by default (CLI --prefilter).

Falsifier fixture (S9): fixed 8-row matrix where
  - rows 0,1 MUST be kept under q=0.25 (extreme bests)
  - rows 6,7 MUST be dropped under q=0.25 (extreme worsts)

promote_ready=false until falsifier exists (it does).
Geometry never enters gyro_rank.hpp.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np


PREFILTER_NAME = "or_quantile"
DEFAULT_Q = 0.25


def or_quantile_mask(X: np.ndarray, q: float = DEFAULT_Q) -> np.ndarray:
    """Return boolean mask: True = keep. Does not rank."""
    if X.ndim != 2 or X.shape[1] < 2:
        raise ValueError(f"or_quantile expects (N, >=2), got {getattr(X, 'shape', None)}")
    if not (0.0 < q <= 1.0):
        raise ValueError(f"q must be in (0,1]; got {q}")
    n = X.shape[0]
    k = max(1, int(np.ceil(q * n)))
    t0 = np.partition(X[:, 0], k - 1)[k - 1]
    t1 = np.partition(X[:, 1], k - 1)[k - 1]
    return (X[:, 0] <= t0) | (X[:, 1] <= t1)


def apply_prefilter(X: np.ndarray, name: str = PREFILTER_NAME, q: float = DEFAULT_Q) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply named prefilter.
    Returns (survivors N'x2 contiguous, keep_mask length N).
    """
    if name != "or_quantile":
        raise ValueError(f"unknown prefilter {name!r}; only or_quantile is defined")
    mask = or_quantile_mask(X, q=q)
    survivors = np.ascontiguousarray(X[mask], dtype=np.float64)
    return survivors, mask


def falsifier_matrix() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Named falsifier fixture (S9).

    Returns (X, must_keep_idx, must_drop_idx).

    Under or_quantile q=0.25 on this 8-row matrix:
      - must_keep rows are extreme bests on at least one objective → kept
      - must_drop rows are extreme worsts on both → dropped
    """
    # lower-is-better
    X = np.asarray([
        [0.01, 0.50],  # 0 best obj0 → must keep
        [0.50, 0.01],  # 1 best obj1 → must keep
        [0.20, 0.40],  # 2 mid
        [0.40, 0.20],  # 3 mid
        [0.30, 0.30],  # 4 mid
        [0.35, 0.35],  # 5 mid
        [0.90, 0.90],  # 6 worst → must drop
        [0.95, 0.95],  # 7 worst → must drop
    ], dtype=np.float64)
    must_keep = np.array([0, 1], dtype=np.int64)
    must_drop = np.array([6, 7], dtype=np.int64)
    return X, must_keep, must_drop


def run_falsifier(q: float = DEFAULT_Q) -> dict:
    """Execute S9: named keep/drop must hold under or_quantile."""
    X, must_keep, must_drop = falsifier_matrix()
    mask = or_quantile_mask(X, q=q)
    kept = set(np.flatnonzero(mask).tolist())
    keep_ok = all(int(i) in kept for i in must_keep)
    drop_ok = all(int(i) not in kept for i in must_drop)
    return {
        "prefilter": PREFILTER_NAME,
        "q": q,
        "must_keep": must_keep.tolist(),
        "must_drop": must_drop.tolist(),
        "kept": sorted(kept),
        "keep_ok": keep_ok,
        "drop_ok": drop_ok,
        "falsifier_ok": keep_ok and drop_ok,
    }
