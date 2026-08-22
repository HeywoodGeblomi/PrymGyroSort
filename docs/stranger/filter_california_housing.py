#!/usr/bin/env python3
"""PGS-STR-001: produce the stranger two-col CSV from the public California Housing URL.

Usage (from repo root):
  python3 docs/stranger/filter_california_housing.py

Writes docs/stranger/california_housing_two_col.csv with exactly 10000 data rows
(first 10000 after selecting median_income + median_house_value and dropping NA).
Full N after filter = 20640; this is the documented ≥10k slice (ticket §3).

Requires: pandas, network access to the public URL in SOURCE.md.
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("pandas required: pip install pandas", file=sys.stderr)
    raise SystemExit(1)

URL = "https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/housing/housing.csv"
OUT = Path(__file__).resolve().parent / "california_housing_two_col.csv"
N_SLICE = 10000

def main() -> int:
    df = pd.read_csv(URL)
    clean = df[["median_income", "median_house_value"]].dropna()
    if clean.shape[0] != 20640:
        print(f"unexpected full size {clean.shape[0]} (expected 20640)", file=sys.stderr)
        return 1
    slice10k = clean.head(N_SLICE)
    slice10k.to_csv(OUT, index=False)
    n = len(slice10k)
    print(f"Wrote {OUT}")
    print(f"  data rows = {n}")
    print(f"  wc -l     = {n + 1} (header + data)")
    print(f"  full after filter = 20640 (use head({N_SLICE}) for the checked slice)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
