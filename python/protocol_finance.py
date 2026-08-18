#!/usr/bin/env python3
"""PrymGyroSort Finance Protocol Adapter v0.1.4 — richer OBI + MDD objectives. Execution sieve only."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Optional
import numpy as np

ADAPTER_VERSION = "0.1.4"

def _norm(x):
    lo, hi = float(x.min()), float(x.max())
    return np.zeros_like(x) if hi - lo < 1e-15 else (x - lo) / (hi - lo)

def synthetic_market(n, seed, n_good):
    rng = np.random.default_rng(seed)
    dislocation = rng.exponential(scale=0.35, size=n)
    obi = rng.uniform(-1.0, 1.0, size=n)
    bid_ask = rng.uniform(0.01, 0.30, size=n)
    depth = rng.uniform(800.0, 40_000.0, size=n)
    mdd = rng.uniform(0.0, 0.08, size=n)
    n_good = min(n_good, n)
    idx = rng.choice(n, size=n_good, replace=False)
    dislocation[idx] = rng.uniform(1.5, 3.5, size=n_good)
    obi[idx] = rng.uniform(0.4, 1.0, size=n_good)
    bid_ask[idx] = rng.uniform(0.005, 0.02, size=n_good)
    depth[idx] = rng.uniform(25_000.0, 80_000.0, size=n_good)
    mdd[idx] = rng.uniform(0.0, 0.01, size=n_good)
    is_good = np.zeros(n, dtype=bool); is_good[idx] = True
    return dislocation, obi, bid_ask, depth, mdd, is_good

def load_csv(path: Path):
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    if data.ndim == 1: data = data.reshape(1, -1)
    if data.shape[1] < 6:
        raise SystemExit(f"[finance] CSV needs ≥6 columns; got {data.shape[1]}")
    a, b, mean = data[:,1].astype(np.float64), data[:,2].astype(np.float64), data[:,3].astype(np.float64)
    bid_ask, depth = data[:,4].astype(np.float64), data[:,5].astype(np.float64)
    dislocation = np.abs((a - b) - mean)
    n = len(dislocation)
    obi = data[:,6].astype(np.float64) if data.shape[1] > 6 else np.zeros(n)
    mdd = data[:,7].astype(np.float64) if data.shape[1] > 7 else np.zeros(n)
    return dislocation, obi, bid_ask, depth, mdd, None

def map_objectives(dislocation, obi, bid_ask, depth, mdd, normalize=True):
    opp_dis = 1.0 / (dislocation + 1e-5)
    opp_obi = (1.0 - np.clip(obi, -1.0, 1.0)) * 0.5
    liq = bid_ask / (depth + 1e-5)
    risk_mdd = np.maximum(mdd, 0.0)
    if normalize:
        opp_dis, opp_obi, liq, risk_mdd = _norm(opp_dis), _norm(opp_obi), _norm(liq), _norm(risk_mdd)
    obj0 = 0.6 * opp_dis + 0.4 * opp_obi
    obj1 = 0.6 * liq + 0.4 * risk_mdd
    return np.column_stack([obj0, obj1]).astype(np.float64)

def compile_finance_matrix(input_path, out_dir: Path, n, seed, n_good, normalize):
    out_dir.mkdir(parents=True, exist_ok=True)
    if input_path is not None and Path(input_path).exists():
        print(f"[*] Finance adapter v{ADAPTER_VERSION}: loading {input_path}")
        dislocation, obi, bid_ask, depth, mdd, is_good = load_csv(Path(input_path)); source = "csv"
    else:
        print(f"[*] Finance adapter v{ADAPTER_VERSION}: synthetic bootstrap")
        dislocation, obi, bid_ask, depth, mdd, is_good = synthetic_market(n, seed, n_good); source = "synthetic"
    matrix = map_objectives(dislocation, obi, bid_ask, depth, mdd, normalize=normalize)
    matrix.tofile(out_dir / "matrix.bin")
    if is_good is not None: np.save(out_dir / "is_good.npy", is_good)
    meta = {"n": int(matrix.shape[0]), "m": 2, "domain": "finance_pair_arbitrage",
            "adapter_version": ADAPTER_VERSION, "source": source, "promote_ready": False,
            "objectives": {"obj0": "opportunity_proxy (dislocation+OBI)", "obj1": "risk_proxy (liq+MDD)"},
            "scope": "execution sieve only; no alpha claim"}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[+] Finance matrix locked N={matrix.shape[0]} promote_ready=false")
    return meta

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=None); p.add_argument("--out-dir", default="work")
    p.add_argument("--n", type=int, default=4096); p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-good", type=int, default=48); p.add_argument("--no-normalize", action="store_true")
    a = p.parse_args()
    compile_finance_matrix(Path(a.input) if a.input else None, Path(a.out_dir), a.n, a.seed, a.n_good, not a.no_normalize)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
