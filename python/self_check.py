#!/usr/bin/env python3
"""PrymGyroSort self-check — real artifact verification. EXTERNAL-clean / path-local only."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=".")
    p.add_argument("--top-frac", type=float, default=0.05)
    p.add_argument("--min-good-recall", type=float, default=0.60)
    p.add_argument("--max-time-ms", type=float, default=50.0)
    args = p.parse_args()
    d = Path(args.dir)
    ranks = np.fromfile(d / "ranks.bin", dtype=np.int32)
    is_good = np.load(d / "is_good.npy")
    n, n_good = len(ranks), int(is_good.sum())
    order = np.argsort(ranks, kind="stable")
    k = max(1, int(args.top_frac * n))
    recall = int(is_good[order[:k]].sum()) / max(n_good, 1)
    mean_good = float(ranks[is_good].mean()) if n_good else float("nan")
    mean_rest = float(ranks[~is_good].mean()) if (~is_good).any() else float("nan")
    ok = recall >= args.min_good_recall and mean_good < mean_rest
    result = {"ok": bool(ok), "n": n, "n_good": n_good, "recall": recall,
              "mean_rank_good": mean_good, "mean_rank_rest": mean_rest}
    (d / "self_check.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print("[PrymGyroSort] SELF-CHECK", "GREEN" if ok else "FAILED")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
