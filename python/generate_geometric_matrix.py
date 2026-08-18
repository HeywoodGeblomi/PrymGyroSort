#!/usr/bin/env python3
"""PrymGyroSort geometric matrix generator (certificate-anchored synthetic)."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np

EIGHT_FIFTHS = 1.6
DEFAULT_N = 4096
DEFAULT_SEED = 728
N_GOOD = 48

def generate(n: int = DEFAULT_N, seed: int = DEFAULT_SEED, n_good: int = N_GOOD):
    rng = np.random.default_rng(seed)
    good_pos = rng.normal(loc=EIGHT_FIFTHS, scale=0.0015, size=n_good)
    good_qr  = rng.uniform(1e-7, 4e-5, size=n_good)
    n_rest = n - n_good
    rest_pos = rng.normal(loc=EIGHT_FIFTHS, scale=0.085, size=n_rest)
    rest_pos += rng.choice([-0.25, 0.0, 0.25], size=n_rest, p=[0.08, 0.84, 0.08])
    rest_qr  = rng.uniform(8e-5, 3e-2, size=n_rest)
    pos = np.concatenate([good_pos, rest_pos])
    qr  = np.concatenate([good_qr, rest_qr])
    obj0 = np.abs(pos - EIGHT_FIFTHS).astype(np.float64)
    obj1 = qr.astype(np.float64)
    matrix = np.column_stack([obj0, obj1])
    perm = rng.permutation(n)
    matrix = matrix[perm]
    is_good = (perm < n_good)
    meta = {
        "n": n, "m": 2, "seed": seed, "n_good": n_good,
        "eight_fifths": EIGHT_FIFTHS,
        "good_pos_mean": float(good_pos.mean()),
        "good_qr_mean": float(good_qr.mean()),
    }
    return matrix, is_good, meta

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=DEFAULT_N)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out-dir", type=str, default=".")
    p.add_argument("--n-good", type=int, default=N_GOOD)
    args = p.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    matrix, is_good, meta = generate(args.n, args.seed, args.n_good)
    matrix.tofile(out / "matrix.bin")
    np.save(out / "is_good.npy", is_good)
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[PrymGyroSort] Wrote matrix.bin N={meta['n']} M=2 good={meta['n_good']} seed={meta['seed']}")

if __name__ == "__main__":
    main()
