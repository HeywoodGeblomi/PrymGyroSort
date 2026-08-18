#!/usr/bin/env python3
"""Multi-Asset Scaling Profiler — rank latency vs concurrent symbols (1→100). Measurement only."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from prym_gyro import rank  # noqa: E402
from ws_crypto_sidecar import book_ticker_to_row, SymbolState  # noqa: E402

def synth_rows_for_symbols(n_symbols, rows_per_symbol, seed):
    rng = np.random.default_rng(seed)
    states = [SymbolState() for _ in range(n_symbols)]
    rows = []
    for _ in range(rows_per_symbol):
        for s, st in enumerate(states):
            mid = 100.0 + s + float(rng.normal(0, 0.5))
            spread = abs(float(rng.normal(0.05, 0.01))) + 0.001
            bid, ask = mid - 0.5 * spread, mid + 0.5 * spread
            bq = abs(float(rng.normal(20, 5))) + 0.1
            aq = abs(float(rng.normal(20, 5))) + 0.1
            row = book_ticker_to_row(bid, ask, bq, aq, st)
            if row is not None:
                rows.append(row)
    return np.ascontiguousarray(np.stack(rows, axis=0), dtype=np.float64)

def map_to_objectives(rows):
    dislocation, obi, bid_ask, depth, mdd = rows[:,0], rows[:,1], rows[:,2], rows[:,3], rows[:,4]
    def _n(x):
        lo, hi = float(x.min()), float(x.max())
        return np.zeros_like(x) if hi - lo < 1e-15 else (x - lo) / (hi - lo)
    opp_dis = _n(1.0 / (dislocation + 1e-5))
    opp_obi = _n((1.0 - np.clip(obi, -1.0, 1.0)) * 0.5)
    liq = _n(bid_ask / (depth + 1e-5))
    risk_mdd = _n(np.maximum(mdd, 0.0))
    return np.ascontiguousarray(
        np.column_stack([0.6*opp_dis+0.4*opp_obi, 0.6*liq+0.4*risk_mdd]), dtype=np.float64)

def bench_once(X, reps):
    rank(X, memory_pressure=False)
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        rank(X, memory_pressure=False)
        times.append((time.perf_counter() - t0) * 1e6)
    arr = np.asarray(times, dtype=np.float64)
    return {"n": int(X.shape[0]), "median_us": float(np.median(arr)),
            "p95_us": float(np.percentile(arr, 95)), "min_us": float(np.min(arr)),
            "mean_us": float(np.mean(arr))}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols-ladder", default="1,2,4,8,16,32,64,100")
    p.add_argument("--rows-per-symbol", type=int, default=64)
    p.add_argument("--reps", type=int, default=25)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(ROOT / "docs" / "MULTI_ASSET_SCALING.json"))
    args = p.parse_args()
    ladder = [int(x) for x in args.symbols_ladder.split(",") if x.strip()]
    print("[multi-asset] latency floor vs concurrent symbols")
    print(f"{'symbols':>8}  {'N_rows':>8}  {'median_us':>10}  {'p95_us':>10}  {'min_us':>10}")
    results = []
    for n_sym in ladder:
        rows = synth_rows_for_symbols(n_sym, args.rows_per_symbol, args.seed + n_sym)
        X = map_to_objectives(rows)
        stats = bench_once(X, reps=args.reps if n_sym <= 32 else max(8, args.reps // 2))
        stats["n_symbols"] = n_sym
        results.append(stats)
        print(f"{n_sym:8d}  {stats['n']:8d}  {stats['median_us']:10.1f}  {stats['p95_us']:10.1f}  {stats['min_us']:10.1f}")
    payload = {"results": results, "rows_per_symbol": args.rows_per_symbol, "reps": args.reps,
               "scope": "latency measurement only; promote_ready=false"}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    md = out.with_suffix(".md")
    lines = ["# Multi-Asset Scaling Profiler", "",
             "| Symbols | N rows | median µs | p95 µs | min µs |",
             "|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['n_symbols']} | {r['n']} | {r['median_us']:.1f} | {r['p95_us']:.1f} | {r['min_us']:.1f} |")
    lines += ["", "Honesty: latency measurement only. Not alpha. `promote_ready=false`.", ""]
    md.write_text("\n".join(lines))
    print(f"[multi-asset] wrote {out} and {md}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
