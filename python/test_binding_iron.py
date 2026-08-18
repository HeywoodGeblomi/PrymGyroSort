#!/usr/bin/env python3
"""Binding iron unit tests — hard reject illegal layouts. promote_ready=false."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "bindings"))
sys.path.insert(0, str(ROOT / "python"))
import prym_gyro_native as native  # noqa: E402
from prym_gyro import rank as py_rank  # noqa: E402

def expect_raise(label, fn):
    try:
        fn()
        print(f"FAIL  {label} — expected exception")
        return False
    except Exception as e:
        print(f"PASS  {label} — {type(e).__name__}: {str(e).split(chr(10))[0][:90]}")
        return True

def expect_ok(label, fn):
    try:
        fn()
        print(f"PASS  {label}")
        return True
    except Exception as e:
        print(f"FAIL  {label} — {e}")
        return False

def main():
    print("[binding-iron] pointer barrier tests")
    ok = total = 0
    n = 128
    X = np.ascontiguousarray(np.random.randn(n, 2), dtype=np.float64)
    ranks = np.empty(n, dtype=np.int32)
    def check(label, good, fn):
        nonlocal ok, total
        total += 1
        ok += int(expect_ok(label, fn) if good else expect_raise(label, fn))
    check("C-contiguous (N,2) float64", True, lambda: native.rank(X, ranks, False))
    check("python helper rank()", True, lambda: py_rank(X))
    check("reject (N,3)", False, lambda: native.rank(np.ascontiguousarray(np.random.randn(n, 3)), ranks, False))
    check("reject (N,)", False, lambda: native.rank(np.ascontiguousarray(np.random.randn(n)), ranks, False))
    check("reject 3-D", False, lambda: native.rank(np.ascontiguousarray(np.random.randn(n, 2, 1)), ranks, False))
    Xf = np.asfortranarray(np.random.randn(n, 2).astype(np.float64))
    check("reject Fortran-order matrix", False, lambda: native.rank(Xf, ranks, False))
    messy = np.ascontiguousarray(np.random.randn(n, 4), dtype=np.float64)[:, ::2]
    check("reject strided matrix", False, lambda: native.rank(messy, ranks.copy(), False))
    check("reject float32", False, lambda: native.rank(np.ascontiguousarray(np.random.randn(n, 2), dtype=np.float32), ranks, False))
    check("reject ranks wrong length", False, lambda: native.rank(X, np.empty(n // 2, dtype=np.int32), False))
    check("reject ranks float64", False, lambda: native.rank(X, np.empty(n, dtype=np.float64), False))
    check("helper copies F-order then ranks", True, lambda: py_rank(Xf))
    print(f"\n[binding-iron] {ok}/{total} passed")
    return 0 if ok == total else 1

if __name__ == "__main__":
    raise SystemExit(main())
