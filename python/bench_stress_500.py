#!/usr/bin/env python3
"""Stress profiler to 500 symbols: churn vs prealloc vs rank-only. Measurement only."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from prym_gyro import rank  # noqa: E402
from ws_crypto_sidecar import SymbolState, book_ticker_to_row  # noqa: E402

def generate_raw_rows(n_symbols, rows_per_symbol, seed):
    rng = np.random.default_rng(seed)
    states = [SymbolState() for _ in range(n_symbols)]
    rows = []
    for _ in range(rows_per_symbol):
        for s, st in enumerate(states):
            mid = 100.0 + 0.1 * s + float(rng.normal(0, 0.4))
            spread = abs(float(rng.normal(0.04, 0.01))) + 1e-3
            bid, ask = mid - 0.5 * spread, mid + 0.5 * spread
            bq = abs(float(rng.normal(15, 4))) + 0.1
            aq = abs(float(rng.normal(15, 4))) + 0.1
            row = book_ticker_to_row(bid, ask, bq, aq, st)
            if row is not None:
                rows.append(row)
    return np.stack(rows, axis=0).astype(np.float64)

def map_objectives_into(rows5, out):
    dislocation, obi, bid_ask, depth, mdd = rows5[:,0], rows5[:,1], rows5[:,2], rows5[:,3], rows5[:,4]
    def _n(x):
        lo, hi = float(x.min()), float(x.max())
        return np.zeros_like(x) if hi - lo < 1e-15 else (x - lo) / (hi - lo)
    opp_dis = _n(1.0 / (dislocation + 1e-5))
    opp_obi = _n((1.0 - np.clip(obi, -1.0, 1.0)) * 0.5)
    liq = _n(bid_ask / (depth + 1e-5))
    risk_mdd = _n(np.maximum(mdd, 0.0))
    out[:, 0] = 0.6 * opp_dis + 0.4 * opp_obi
    out[:, 1] = 0.6 * liq + 0.4 * risk_mdd

def map_objectives_churn(rows5):
    out = np.empty((rows5.shape[0], 2), dtype=np.float64)
    map_objectives_into(rows5, out)
    return np.ascontiguousarray(out)

def _stats(times_us):
    a = np.asarray(times_us, dtype=np.float64)
    return {"median_us": float(np.median(a)), "p95_us": float(np.percentile(a, 95)), "min_us": float(np.min(a))}

def bench_churn(rows5, reps):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        X = map_objectives_churn(rows5)
        rank(X, memory_pressure=False)
        times.append((time.perf_counter() - t0) * 1e6)
    return _stats(times)

def bench_prealloc(rows5, reps):
    X = np.empty((rows5.shape[0], 2), dtype=np.float64)
    map_objectives_into(rows5, X); rank(X, memory_pressure=False)
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        map_objectives_into(rows5, X)
        rank(X, memory_pressure=False)
        times.append((time.perf_counter() - t0) * 1e6)
    return _stats(times)

def bench_rank_only(rows5, reps):
    X = map_objectives_churn(rows5); rank(X, memory_pressure=False)
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        rank(X, memory_pressure=False)
        times.append((time.perf_counter() - t0) * 1e6)
    return _stats(times)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ladder", default="1,4,16,64,100,200,350,500")
    ap.add_argument("--rows-per-symbol", type=int, default=64)
    ap.add_argument("--reps", type=int, default=12)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "docs" / "STRESS_500.json"))
    args = ap.parse_args()
    ladder = [int(x) for x in args.ladder.split(",") if x.strip()]
    print("[stress-500] prealloc vs churn vs rank-only")
    print(f"{'sym':>5} {'N':>7} {'churn_med':>10} {'pre_med':>10} {'rank_med':>10} {'churn-pre':>10} {'rank/pre%':>10}")
    results = []
    for n_sym in ladder:
        rows5 = generate_raw_rows(n_sym, args.rows_per_symbol, args.seed + n_sym)
        n = rows5.shape[0]
        reps = args.reps if n_sym <= 100 else max(5, args.reps // 2)
        churn, pre, rok = bench_churn(rows5, reps), bench_prealloc(rows5, reps), bench_rank_only(rows5, reps)
        delta = churn["median_us"] - pre["median_us"]
        frac = 100.0 * rok["median_us"] / pre["median_us"] if pre["median_us"] > 0 else 0.0
        results.append({"n_symbols": n_sym, "n_rows": n, "churn": churn, "prealloc": pre, "rank_only": rok,
                        "churn_minus_prealloc_us": delta, "rank_fraction_of_prealloc_pct": frac})
        print(f"{n_sym:5d} {n:7d} {churn['median_us']:10.1f} {pre['median_us']:10.1f} {rok['median_us']:10.1f} {delta:10.1f} {frac:9.1f}%")
    payload = {"results": results, "rows_per_symbol": args.rows_per_symbol, "reps": args.reps,
               "interpretation": "If rank_only ≈ prealloc, kernel dominates; Shadow-Ring will not cut latency by orders of magnitude.",
               "scope": "latency measurement only; promote_ready=false"}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    md = out.with_suffix(".md")
    lines = ["# Stress-500: Prealloc vs Churn vs Rank-Only", "",
             "| Symbols | N | churn µs | prealloc µs | rank-only µs | churn−pre µs | rank/pre % |",
             "|---:|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['n_symbols']} | {r['n_rows']} | {r['churn']['median_us']:.1f} | {r['prealloc']['median_us']:.1f} | {r['rank_only']['median_us']:.1f} | {r['churn_minus_prealloc_us']:.1f} | {r['rank_fraction_of_prealloc_pct']:.1f}% |")
    lines += ["", "## Interpretation", "", payload["interpretation"], "", "Honesty: measurement only. `promote_ready=false`.", ""]
    md.write_text("\n".join(lines))
    print(f"[stress-500] wrote {out} and {md}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
