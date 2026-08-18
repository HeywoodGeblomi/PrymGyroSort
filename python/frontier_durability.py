#!/usr/bin/env python3
"""Frontier durability — symbol-stable Jaccard/survival of rank-1 and top-frac. promote_ready=false."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from prym_gyro import rank  # noqa: E402
from prefilter_rank import filter_quantile  # noqa: E402

def jaccard(a, b):
    sa, sb = set(int(x) for x in a.tolist()), set(int(x) for x in b.tolist())
    if not sa and not sb: return 1.0
    if not sa or not sb: return 0.0
    return len(sa & sb) / len(sa | sb)

def survival(prev, cur):
    return 1.0 if prev.size == 0 else float(np.isin(prev, cur).mean())

class SymbolBook:
    def __init__(self, n_symbols, seed):
        self.n = n_symbols
        self.rng = np.random.default_rng(seed)
        self.mid = 100.0 + 0.5 * np.arange(n_symbols, dtype=np.float64)
        self.peak = self.mid.copy()
        self.ema = self.mid.copy()
        self.spread = np.full(n_symbols, 0.05, dtype=np.float64)
        self.bid_qty = np.full(n_symbols, 20.0, dtype=np.float64)
        self.ask_qty = np.full(n_symbols, 20.0, dtype=np.float64)

    def step(self, tick):
        shock = self.rng.normal(0, 0.15, size=self.n)
        self.mid = self.mid + 0.02 * np.sin(0.1 * tick + 0.01 * np.arange(self.n)) + shock
        self.ema = 0.9 * self.ema + 0.1 * self.mid
        self.peak = np.maximum(0.98 * self.peak, self.mid)
        self.spread = np.clip(self.spread + self.rng.normal(0, 0.002, size=self.n), 0.005, 0.5)
        self.bid_qty = np.clip(self.bid_qty + self.rng.normal(0, 1.0, size=self.n), 0.5, 200)
        self.ask_qty = np.clip(self.ask_qty + self.rng.normal(0, 1.0, size=self.n), 0.5, 200)
        dislocation = np.abs(self.mid - self.ema)
        depth = self.bid_qty + self.ask_qty
        obi = (self.bid_qty - self.ask_qty) / depth
        mdd = np.where(self.peak > 1e-12, np.maximum(0.0, (self.peak - self.mid) / self.peak), 0.0)
        def _n(x):
            lo, hi = float(x.min()), float(x.max())
            return np.zeros_like(x) if hi - lo < 1e-15 else (x - lo) / (hi - lo)
        obj0 = 0.6 * _n(1.0 / (dislocation + 1e-5)) + 0.4 * _n((1.0 - np.clip(obi, -1, 1)) * 0.5)
        obj1 = 0.6 * _n(self.spread / (depth + 1e-5)) + 0.4 * _n(mdd)
        return np.ascontiguousarray(np.column_stack([obj0, obj1]), dtype=np.float64)

def fronts(X, top_frac, use_quantile, q):
    t0 = time.perf_counter()
    n = X.shape[0]
    if use_quantile:
        keep = filter_quantile(X, q)
        idx = np.flatnonzero(keep)
        ranks_p = rank(np.ascontiguousarray(X[idx]), memory_pressure=False)
        order = np.argsort(ranks_p, kind="stable")
        top_k = max(1, int(top_frac * n))
        top = idx[order[:top_k]]
        r1 = idx[ranks_p == ranks_p.min()]
    else:
        ranks = rank(X, memory_pressure=False)
        r1 = np.flatnonzero(ranks == ranks.min())
        top = np.argsort(ranks, kind="stable")[: max(1, int(top_frac * n))]
    return r1, top, (time.perf_counter() - t0) * 1e3

def run_durability(n_symbols, ticks, top_frac, use_quantile, q, seed):
    book = SymbolBook(n_symbols, seed)
    prev_r1 = prev_top = None
    j_r1, j_top, s_r1, s_top, lat = [], [], [], [], []
    for t in range(ticks):
        X = book.step(t)
        r1, top, ms = fronts(X, top_frac, use_quantile, q)
        lat.append(ms)
        if prev_r1 is not None:
            j_r1.append(jaccard(prev_r1, r1))
            j_top.append(jaccard(prev_top, top))
            s_r1.append(survival(prev_r1, r1))
            s_top.append(survival(prev_top, top))
        prev_r1, prev_top = r1, top
    def med(xs):
        return float(np.median(xs)) if xs else 0.0
    return {"n_symbols": n_symbols, "ticks": ticks,
            "path": "quantile" if use_quantile else "full", "q": q if use_quantile else None,
            "jaccard_rank1_median": med(j_r1), "jaccard_top_median": med(j_top),
            "survival_rank1_median": med(s_r1), "survival_top_median": med(s_top),
            "latency_ms_median": med(lat),
            "jaccard_rank1_series": [round(x, 4) for x in j_r1],
            "jaccard_top_series": [round(x, 4) for x in j_top]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=int, default=100)
    ap.add_argument("--ticks", type=int, default=50)
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "docs" / "FRONTIER_DURABILITY.json"))
    args = ap.parse_args()
    print("[durability] symbol-stable frontier across ticks")
    results = []
    for use_q in (False, True):
        r = run_durability(args.symbols, args.ticks, args.top_frac, use_q, args.q, args.seed)
        results.append(r)
        print(f"{r['path']:>9} sym={r['n_symbols']} J@r1={r['jaccard_rank1_median']:.3f} "
              f"J@top={r['jaccard_top_median']:.3f} S@r1={r['survival_rank1_median']:.3f} "
              f"S@top={r['survival_top_median']:.3f} ms={r['latency_ms_median']:.2f}")
    payload = {"results": [{k: v for k, v in r.items() if not k.endswith("_series")} for r in results],
               "scope": "Symbol-stable synthetic drift. Observational only. promote_ready=false."}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    md = out.with_suffix(".md")
    lines = ["# Frontier Durability (symbol-stable)", "",
             "| path | symbols | J@rank1 | J@top | S@rank1 | S@top | median ms |",
             "|:---|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['path']} | {r['n_symbols']} | {r['jaccard_rank1_median']:.3f} | "
                     f"{r['jaccard_top_median']:.3f} | {r['survival_rank1_median']:.3f} | "
                     f"{r['survival_top_median']:.3f} | {r['latency_ms_median']:.2f} |")
    lines += ["", "Honesty: synthetic observational metric. `promote_ready=false`.", ""]
    md.write_text("\n".join(lines))
    print(f"[durability] wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
