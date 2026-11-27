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


def rank_fenwick_ref(matrix: np.ndarray) -> np.ndarray:
    """F3 Fenwick oracle: exact_rank_2d_fenwick only (no controller)."""
    X = np.ascontiguousarray(matrix, dtype=np.float64)
    if X.ndim != 2 or X.shape[1] != 2:
        raise ValueError("matrix must be (N, 2)")
    ranks = np.empty(X.shape[0], dtype=np.int32)
    _native.rank_fenwick_ref(X, ranks)
    return ranks


def exact_rank_2d(xs, ys) -> np.ndarray:
    """Rank two score arrays with exact_rank_2d_fenwick.

    xs and ys may be numpy arrays or lists. Lower is better, matching the
    kernel. Returns a new int32 rank/layer vector of the same length.
    """
    x = np.ascontiguousarray(xs, dtype=np.float64).reshape(-1)
    y = np.ascontiguousarray(ys, dtype=np.float64).reshape(-1)
    if x.shape[0] != y.shape[0]:
        raise ValueError(f"xs and ys length mismatch: {x.shape[0]} vs {y.shape[0]}")
    return np.asarray(_native.exact_rank_2d(x, y), dtype=np.int32)


def kernel_times_ms(matrix: np.ndarray, reps: int) -> dict:
    """Time exact_rank_2d_fenwick only. The matrix is already in memory."""
    X = np.ascontiguousarray(matrix, dtype=np.float64)
    if X.ndim != 2 or X.shape[1] != 2:
        raise ValueError("matrix must be (N, 2)")
    info = dict(_native.kernel_times_ms(X, int(reps)))
    info["ranks"] = np.asarray(info["ranks"], dtype=np.int32)
    info["times_ms"] = [float(v) for v in info["times_ms"]]
    return info


def write_score_receipt(path, *, xs, ys, input_path, columns, pair_sieve_version: str) -> dict:
    """Rank xs, ys and write a receipt through receipt.py.

    xs and ys are the kernel-orientation scores (lower is better). columns
    record the names and senses of the source file.
    """
    from receipt import build_receipt, write_receipt

    x = np.ascontiguousarray(xs, dtype=np.float64).reshape(-1)
    y = np.ascontiguousarray(ys, dtype=np.float64).reshape(-1)
    ranks = exact_rank_2d(x, y)
    adjusted = np.column_stack([x, y])
    receipt = build_receipt(
        input_path=Path(input_path) if input_path else None,
        row_count=int(x.shape[0]),
        columns=columns,
        ranks=ranks,
        adjusted=adjusted,
        pair_sieve_version=pair_sieve_version,
    )
    write_receipt(Path(path), receipt)
    return receipt


__all__ = [
    "rank",
    "rank_report",
    "rank_fenwick_ref",
    "exact_rank_2d",
    "kernel_times_ms",
    "write_score_receipt",
]
