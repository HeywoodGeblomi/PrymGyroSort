"""
GYR-SIEVE-001/002 prefilters — drop-only, never rank.

Named prefilters:
  or_quantile  — bottom-q on obj0 OR obj1 (Track 3)
  prym         — path-local residual band (Ticket B / GYR-SIEVE-002)

  prym thresholds are path-local certificate-style gates derived from the
  documented seed-728 residual band in prym-eigenform-pipeline-d12 /
  PrymGyroSort geometric ensemble (obj0 ≈ |pos−8/5|, obj1 ≈ QR residual).
  They do NOT claim global Lyapunov or spectrum.

Kill-switch: --prefilter off by default.
Geometry never enters gyro_rank.hpp. promote_ready=false.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np

PREFILTER_NAME = "or_quantile"
DEFAULT_Q = 0.25

# Path-local residual band (Ticket B). Documented thresholds — not spectrum claims.
PRYM_TAU0 = 0.08   # max |pos − 8/5|-style residual (obj0)
PRYM_TAU1 = 1e-4   # max QR residual (obj1)
PRYM_SOURCE = (
    "path-local residual band; thresholds from PrymGyroSort geometric ensemble / "
    "prym-eigenform-pipeline-d12 seed-728 certificate style (not global spectrum)"
)


def or_quantile_mask(X: np.ndarray, q: float = DEFAULT_Q) -> np.ndarray:
    """Keep bottom-q fraction on obj0 OR obj1. No ranks."""
    if X.ndim != 2 or X.shape[1] < 2:
        raise ValueError(f"or_quantile expects (N, >=2), got {getattr(X, 'shape', None)}")
    if not (0.0 < q <= 1.0):
        raise ValueError(f"q must be in (0,1]; got {q}")
    n = X.shape[0]
    k = max(1, int(np.ceil(q * n)))
    t0 = np.partition(X[:, 0], k - 1)[k - 1]
    t1 = np.partition(X[:, 1], k - 1)[k - 1]
    return (X[:, 0] <= t0) | (X[:, 1] <= t1)


def prym_mask(X: np.ndarray, tau0: float = PRYM_TAU0, tau1: float = PRYM_TAU1) -> np.ndarray:
    """
    Keep rows inside the path-local residual band: obj0 <= tau0 AND obj1 <= tau1.
    Drop-only. No ranks. No third score.
    """
    if X.ndim != 2 or X.shape[1] < 2:
        raise ValueError(f"prym expects (N, >=2), got {getattr(X, 'shape', None)}")
    return (X[:, 0] <= tau0) & (X[:, 1] <= tau1)


def apply_prefilter(
    X: np.ndarray,
    name: str = PREFILTER_NAME,
    q: float = DEFAULT_Q,
    tau0: float = PRYM_TAU0,
    tau1: float = PRYM_TAU1,
) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (survivors N'x2 contiguous, keep_mask length N)."""
    if name == "or_quantile":
        mask = or_quantile_mask(X, q=q)
    elif name == "prym":
        mask = prym_mask(X, tau0=tau0, tau1=tau1)
    else:
        raise ValueError(f"unknown prefilter {name!r}; known: or_quantile, prym")
    survivors = np.ascontiguousarray(X[mask], dtype=np.float64)
    return survivors, mask


def falsifier_matrix() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """or_quantile S9 fixture (unchanged)."""
    X = np.asarray([
        [0.01, 0.50],
        [0.50, 0.01],
        [0.20, 0.40],
        [0.40, 0.20],
        [0.30, 0.30],
        [0.35, 0.35],
        [0.90, 0.90],
        [0.95, 0.95],
    ], dtype=np.float64)
    must_keep = np.array([0, 1], dtype=np.int64)
    must_drop = np.array([6, 7], dtype=np.int64)
    return X, must_keep, must_drop


def falsifier_matrix_prym() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Ticket B S9: distinct from or_quantile fixture.

    Under prym residual band (tau0=0.08, tau1=1e-4):
      - must_keep: deep inside band
      - must_drop: outside band on at least one residual
    """
    X = np.asarray([
        [0.001, 1e-6],   # 0 deep inside → must keep
        [0.010, 5e-5],   # 1 inside → must keep
        [0.050, 8e-5],   # 2 inside edge → keep
        [0.070, 9e-5],   # 3 inside edge → keep
        [0.100, 1e-6],   # 4 obj0 outside → must drop
        [0.001, 5e-4],   # 5 obj1 outside → must drop
        [0.500, 1e-2],   # 6 both outside → must drop
        [1.000, 1e-1],   # 7 both outside → must drop
    ], dtype=np.float64)
    must_keep = np.array([0, 1], dtype=np.int64)
    must_drop = np.array([4, 5, 6, 7], dtype=np.int64)
    return X, must_keep, must_drop


def run_falsifier(q: float = DEFAULT_Q, name: str = "or_quantile") -> dict:
    """S9: named keep/drop. name=or_quantile | prym."""
    if name == "prym":
        X, must_keep, must_drop = falsifier_matrix_prym()
        mask = prym_mask(X)
        meta = {"tau0": PRYM_TAU0, "tau1": PRYM_TAU1, "source": PRYM_SOURCE}
    else:
        X, must_keep, must_drop = falsifier_matrix()
        mask = or_quantile_mask(X, q=q)
        meta = {"q": q}
    kept = set(np.flatnonzero(mask).tolist())
    keep_ok = all(int(i) in kept for i in must_keep)
    drop_ok = all(int(i) not in kept for i in must_drop)
    return {
        "prefilter": name,
        **meta,
        "must_keep": must_keep.tolist(),
        "must_drop": must_drop.tolist(),
        "kept": sorted(kept),
        "keep_ok": keep_ok,
        "drop_ok": drop_ok,
        "falsifier_ok": keep_ok and drop_ok,
    }
