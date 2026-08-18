#!/usr/bin/env python3
"""Durability stress: push shock noise until quantile diverges from full. promote_ready=false."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from frontier_durability import SymbolBook, fronts, jaccard, survival  # noqa: E402
from prefilter_rank import filter_quantile  # noqa: E402

class NoisySymbolBook(SymbolBook):
    def __init__(self, n_symbols, seed, shock_sigma):
        super().__init__(n_symbols, seed)
        self.shock_sigma = shock_sigma
    def step(self, tick):
        shock = self.rng.normal(0, self.shock_sigma, size=self.n)
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

def run_path(book, ticks, top_frac, use_q, q):
    prev_r1 = prev_top = None
    j_r1, j_top, s_r1, s_top = [], [], [], []
    for t in range(ticks):
        X = book.step(t)
        r1, top, _ = fronts(X, top_frac, use_q, q)
        if prev_r1 is not None:
            j_r1.append(jaccard(prev_r1, r1)); j_top.append(jaccard(prev_top, top))
            s_r1.append(survival(prev_r1, r1)); s_top.append(survival(prev_top, top))
        prev_r1, prev_top = r1, top
    def med(xs): return float(np.median(xs)) if xs else 0.0
    return {"jaccard_rank1": med(j_r1), "jaccard_top": med(j_top),
            "survival_rank1": med(s_r1), "survival_top": med(s_top)}

def within_tick_agreement(n_symbols, seed, sigma, ticks, top_frac, q):
    book = NoisySymbolBook(n_symbols, seed, sigma)
    agr1, atop = [], []
    for t in range(ticks):
        X = book.step(t)
        r1f, topf, _ = fronts(X, top_frac, False, q)
        r1q, topq, _ = fronts(X, top_frac, True, q)
        agr1.append(jaccard(r1f, r1q)); atop.append(jaccard(topf, topq))
    return float(np.median(agr1)), float(np.median(atop))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=int, default=100)
    ap.add_argument("--ticks", type=int, default=40)
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sigmas", default="0.05,0.15,0.30,0.50,0.80,1.20,2.00")
    ap.add_argument("--break-delta", type=float, default=0.10)
    ap.add_argument("--out", default=str(ROOT / "docs" / "DURABILITY_STRESS.json"))
    args = ap.parse_args()
    sigmas = [float(x) for x in args.sigmas.split(",") if x.strip()]
    print("[durability-stress] noise ladder")
    rows = []
    first_break = None
    for sigma in sigmas:
        full = run_path(NoisySymbolBook(args.symbols, args.seed, sigma), args.ticks, args.top_frac, False, args.q)
        quant = run_path(NoisySymbolBook(args.symbols, args.seed, sigma), args.ticks, args.top_frac, True, args.q)
        d_j = abs(full["jaccard_top"] - quant["jaccard_top"])
        d_s = abs(full["survival_top"] - quant["survival_top"])
        agree_r1, agree_top = within_tick_agreement(args.symbols, args.seed, sigma, args.ticks, args.top_frac, args.q)
        broken = d_j >= args.break_delta or d_s >= args.break_delta or agree_top < 1.0 - args.break_delta
        if broken and first_break is None: first_break = sigma
        print(f"sigma={sigma:.2f} J@top f/q={full['jaccard_top']:.3f}/{quant['jaccard_top']:.3f} "
              f"agree@top={agree_top:.3f} break={'YES' if broken else 'no'}")
        rows.append({"sigma": sigma, "full": full, "quantile": quant, "delta_jaccard_top": d_j,
                     "delta_survival_top": d_s, "within_tick_agree_rank1": agree_r1,
                     "within_tick_agree_top": agree_top, "broken": broken})
    payload = {"results": rows, "first_break_sigma": first_break, "break_delta": args.break_delta,
               "definitions": {"S@rank1": "|prev_rank1 ∩ cur_rank1|/|prev_rank1|",
                               "Jaccard": "|A∩B|/|A∪B| on symbol-ID sets",
                               "within_tick_agree": "Jaccard(full_front, quantile_front) same X"},
               "scope": "Stress only. promote_ready=false."}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    md = out.with_suffix(".md")
    lines = ["# Durability Stress — Quantile vs Full under noise", "",
             f"First break σ: `{first_break}`" if first_break else "**No break** on tested ladder (including within-tick agree@top).", "",
             "| σ | J@top full | J@top q | agree@top | ΔJ | break |", "|---:|---:|---:|---:|---:|:---|"]
    for r in rows:
        lines.append(f"| {r['sigma']:.2f} | {r['full']['jaccard_top']:.3f} | {r['quantile']['jaccard_top']:.3f} | "
                     f"{r['within_tick_agree_top']:.3f} | {r['delta_jaccard_top']:.3f} | {'YES' if r['broken'] else 'no'} |")
    lines += ["", "## Definitions", "",
              "- **S@rank1**: fraction of previous rank-1 *set* still in rank-1 — not one asset stays best.",
              "- **Jaccard**: set union/intersection on symbol IDs.",
              "- **within-tick agree**: same-X full vs quantile front membership.",
              "", "`promote_ready=false`", ""]
    md.write_text("\n".join(lines))
    print(f"first_break={first_break} wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
