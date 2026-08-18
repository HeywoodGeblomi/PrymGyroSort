#!/usr/bin/env python3
"""Long-horizon durability on production sieve path (static q + native M=2). promote_ready=false."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from frontier_durability import jaccard, survival  # noqa: E402
from prefilter_rank import filter_quantile  # noqa: E402
from prym_gyro import rank  # noqa: E402
from test_kinetic_match import DriftBook  # noqa: E402

def sieve_front(X, q, top_frac):
    n = X.shape[0]
    if q is not None:
        keep = filter_quantile(X, q)
        idx = np.flatnonzero(keep)
        ranks_p = rank(np.ascontiguousarray(X[idx]), memory_pressure=n >= 65536)
        order = np.argsort(ranks_p, kind="stable")
        top = idx[order[: max(1, int(top_frac * n))]]
        r1 = idx[ranks_p == ranks_p.min()]
    else:
        ranks = rank(X, memory_pressure=n >= 65536)
        r1 = np.flatnonzero(ranks == ranks.min())
        top = np.argsort(ranks, kind="stable")[: max(1, int(top_frac * n))]
    return r1, top

def half_life(series, threshold=0.5):
    if not series: return None
    for i, s in enumerate(series):
        if s < threshold:
            if i == 0: return 0.0
            prev = series[i - 1]
            if prev == s: return float(i)
            return (i - 1) + (prev - threshold) / (prev - s)
    return None

def run_horizon(n_symbols, ticks, sigma, q, top_frac, seed):
    book = DriftBook(n_symbols, seed, sigma)
    prev_r1 = prev_top = origin_r1 = origin_top = None
    j_r1, j_top, s_r1, s_top = [], [], [], []
    s_origin_top, s_origin_r1, lat = [], [], []
    for t in range(ticks):
        X = book.step(t)["static"]
        t0 = time.perf_counter()
        r1, top = sieve_front(X, q, top_frac)
        lat.append((time.perf_counter() - t0) * 1e3)
        if t == 0:
            origin_r1, origin_top = r1, top
        else:
            s_origin_top.append(survival(origin_top, top))
            s_origin_r1.append(survival(origin_r1, r1))
        if prev_r1 is not None:
            j_r1.append(jaccard(prev_r1, r1)); j_top.append(jaccard(prev_top, top))
            s_r1.append(survival(prev_r1, r1)); s_top.append(survival(prev_top, top))
        prev_r1, prev_top = r1, top
    def med(xs): return float(np.median(xs)) if xs else 0.0
    return {
        "n_symbols": n_symbols, "ticks": ticks, "sigma": sigma,
        "path": f"quantile_q={q}" if q is not None else "full", "top_frac": top_frac,
        "jaccard_top_median": med(j_top), "survival_top_median": med(s_top),
        "survival_rank1_median": med(s_r1), "jaccard_rank1_median": med(j_r1),
        "half_life_origin_S_top": half_life(s_origin_top, 0.5),
        "origin_S_top_at_50": float(s_origin_top[49]) if len(s_origin_top) > 49 else None,
        "origin_S_top_at_100": float(s_origin_top[99]) if len(s_origin_top) > 99 else None,
        "origin_S_top_at_250": float(s_origin_top[249]) if len(s_origin_top) > 249 else None,
        "origin_S_top_final": float(s_origin_top[-1]) if s_origin_top else None,
        "latency_ms_median": med(lat),
        "survival_top_series": [round(x, 4) for x in s_top],
        "origin_survival_top_series": [round(x, 4) for x in s_origin_top],
        "jaccard_top_series": [round(x, 4) for x in j_top],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=int, default=100)
    ap.add_argument("--ticks", type=int, default=500)
    ap.add_argument("--sigma", type=float, default=0.15)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "docs" / "SIEVE_DURABILITY_HORIZON.json"))
    args = ap.parse_args()
    print(f"[horizon] symbols={args.symbols} ticks={args.ticks} sigma={args.sigma}")
    rows = []
    for q in (None, args.q):
        r = run_horizon(args.symbols, args.ticks, args.sigma, q, args.top_frac, args.seed)
        rows.append(r)
        print(f"  {r['path']:>16} J@top={r['jaccard_top_median']:.3f} S@top={r['survival_top_median']:.3f} "
              f"origin_S@100={r['origin_S_top_at_100']} half_life_origin={r['half_life_origin_S_top']}")
    payload = {"results": [{k: v for k, v in r.items() if not k.endswith("_series")} for r in rows],
               "scope": "Synthetic observational. Production sieve path. promote_ready=false."}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    md = out.with_suffix(".md")
    lines = ["# Sieve Durability Horizon (production path)", "",
             f"symbols={args.symbols}, ticks={args.ticks}, sigma={args.sigma}", "",
             "| path | J@top | S@top | origin S@50 | origin S@100 | origin S@final | ms |",
             "|:---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['path']} | {r['jaccard_top_median']:.3f} | {r['survival_top_median']:.3f} | "
                     f"{r['origin_S_top_at_50']} | {r['origin_S_top_at_100']} | {r['origin_S_top_final']} | "
                     f"{r['latency_ms_median']:.3f} |")
    lines += ["", "Consecutive-tick median S@top≈0.60 (local durability).",
              "Origin front decays fast under σ=0.15 (S@100≈0). High turnover, not a frozen elite set.",
              "", "`promote_ready=false`", ""]
    md.write_text("\n".join(lines))
    print(f"[horizon] wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
