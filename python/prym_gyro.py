"""
PrymGyroSort — zero-copy helper (GyroRank v0.2)

Usage:
  import numpy as np
  from prym_gyro import rank

  X = np.ascontiguousarray(objs, dtype=np.float64)  # (N, 2)
  ranks = rank(X)  # int32[N]

memory_pressure defaults to False. On GyroRank v0.2 it is a no-op for
algorithm selection (Fenwick-only for exact M=2). Kept for API compatibility.
"""
from __future__ import annotations

from pathlib import Path
import sys
import numpy as np

_BIND = Path(__file__).resolve().parent / "bindings"
if _BIND.is_dir() and str(_BIND) not in sys.path:
    sys.path.insert(0, str(_BIND))

try:
    import prym_gyro_native as _native
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "prym_gyro_native not built. From repo root:\n"
        "  cd python/bindings && python3 setup.py build_ext --inplace\n"
        f"Original error: {e}"
    ) from e


def rank(matrix: np.ndarray, memory_pressure: bool = False) -> np.ndarray:
    """Rank an (N, 2) float64 matrix. memory_pressure is currently a no-op on v0.2."""
    X = np.ascontiguousarray(matrix, dtype=np.float64)
    if X.ndim != 2:
        raise ValueError("matrix must be 2-D")
    n = X.shape[0]
    ranks = np.empty(n, dtype=np.int32)
    _native.rank(X, ranks, bool(memory_pressure))
    return ranks


def rank_report(matrix: np.ndarray, memory_pressure: bool = False) -> dict:
    """Rank and return strategy metadata. memory_pressure is currently a no-op on v0.2."""
    X = np.ascontiguousarray(matrix, dtype=np.float64)
    n = X.shape[0]
    ranks = np.empty(n, dtype=np.int32)
    info = dict(_native.rank_report(X, ranks, bool(memory_pressure)))
    info["ranks"] = ranks
    return info


__all__ = ["rank", "rank_report"]
