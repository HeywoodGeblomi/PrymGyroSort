#!/usr/bin/env python3
"""Weak-dominance tie cases for the M=2 Fenwick kernel.

Identical (x, y) rows stay the same rank. Same-x with a better y is a
dominator. Smaller-x with the same y is a dominator. examples/book.csv
contains 6 tie-dominance pairs (3 same-x/better-y, 3 same-y/better-x) yet
the golden identity was unchanged by the equal-x batching bug, so the
golden hash alone does not test ties.
"""
from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from prym_gyro import rank as native_rank

BOOK = ROOT / "examples" / "book.csv"
# examples/book.csv has 6 tie-dominance pairs, but the equal-x batching bug
# did not move any book layer, so this hash alone does not test ties.
BOOK_IDENTITY = "968b5b2b85e9c402664f05a44b240ae657b70a57d56ef59e392cd567b12e0121"


def ranks_of(rows) -> list[int]:
    X = np.ascontiguousarray(rows, dtype=np.float64)
    return [int(v) for v in native_rank(X)]


def main() -> int:
    fails = []

    def check(name: str, rows, expected: list[int]) -> None:
        got = ranks_of(rows)
        if got != expected:
            fails.append(f"{name}: got {got} expected {expected}")
            print(f"FAIL {name}: got {got} expected {expected}")
        else:
            print(f"PASS {name}: {got}")

    # Identical coordinates. Neither row dominates the other.
    check("identical_xy", [[1.0, 1.0], [1.0, 1.0]], [1, 1])

    # A1209 (0.78, 2.657) vs A3715 (0.78, 2.548), higher-is-better,
    # passed to the kernel as the negated lower-is-better pair.
    # The heavier row dominates the tied-length row.
    check(
        "same_x_better_y_a1209_a3715",
        [[-0.78, -2.657], [-0.78, -2.548]],
        [1, 2],
    )

    # Strictly smaller x, equal y. Layers 1 then 2.
    check("smaller_x_equal_y", [[0.0, 0.0], [1.0, 0.0]], [1, 2])

    with BOOK.open(newline="") as f:
        pts = [(float(r["risk"]), float(r["cost"])) for r in csv.DictReader(f)]
    book_ranks = np.ascontiguousarray(ranks_of(pts), dtype=np.int32)
    digest = hashlib.sha256(book_ranks.tobytes()).hexdigest()
    if digest != BOOK_IDENTITY:
        fails.append(f"book identity {digest}")
        print(f"FAIL book_identity: {digest}")
    else:
        print(f"PASS book_identity: {digest}")

    if fails:
        print(f"FAIL {len(fails)}")
        return 1
    print("GREEN: weak-dominance tie cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
