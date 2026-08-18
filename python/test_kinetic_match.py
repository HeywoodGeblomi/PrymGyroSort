#!/usr/bin/env python3
"""Kinetic A/B match: velocity transform vs static baseline. Ship only if beats durability with agree held."""
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

class DriftBook:
    def __init__(self, n, seed, shock_sigma=0.15):
        self.n, self.rng, self.sigma = n, np.random.default_rng(seed), shock_sigma
        self.mid = 100.0 + 0.5 * np.arange(n, dtype=np.float64)
        self.peak, self.ema = self.mid.copy(), self.mid.copy()
        self.spread = np.full(n, 0.05, dtype=np.float64)
        self.bid_qty = np.full(n, 20.0, dtype=np.float64)
        self.ask_qty = np.full(n, 20.0, dtype=np.float64)
        self.prev_obj = None
    def _norm(self, x):
        lo, hi = float(x.min()), float(x.max())
        return np.zeros_like(x) if hi - lo < 1e-15 else (x - lo) / (hi - lo)
    def step(self, tick):
        shock = self.rng.normal(0, self.sigma, size=self.n)
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
        obj0 = 0.6 * self._norm(1.0 / (dislocation + 1e-5)) + 0.4 * self._norm((1.0 - np.clip(obi, -1, 1)) * 0.5)
        obj1 = 0.6 * self._norm(self.spread / (depth + 1e-5)) + 0.4 * self._norm(mdd)
        static = np.ascontiguousarray(np.column_stack([obj0, obj1]), dtype=np.float64)
        delta = np.zeros_like(static) if self.prev_obj is None else static - self.prev_obj
        self.prev_obj = static.copy()
        return {"static": static, "delta": delta}

def kinetic_transform(static, delta, alpha, beta):
    scale0 = 1.0 + alpha * np.maximum(delta[:, 0], 0.0)
    scale1 = np.clip(1.0 - beta * np.maximum(-delta[:, 1], 0.0), 0.05, None)
    return np.ascontiguousarray(np.column_stack([static[:, 0] * scale0, static[:, 1] * scale1]), dtype=np.float64)

def front_from_X(X, top_frac, q):
    n = X.shape[0]
    t0 = time.perf_counter()
    if q is not None:
        keep = filter_quantile(X, q)
        idx = np.flatnonzero(keep)
        ranks = rank(np.ascontiguousarray(X[idx]), memory_pressure=False)
        order = np.argsort(ranks, kind="stable")
        top = idx[order[: max(1, int(top_frac * n))]]
        r1 = idx[ranks == ranks.min()]
    else:
        ranks = rank(X, memory_pressure=False)
        r1 = np.flatnonzero(ranks == ranks.min())
        top = np.argsort(ranks, kind="stable")[: max(1, int(top_frac * n))]
    return r1, top, (time.perf_counter() - t0) * 1e3

def run_group(book, ticks, top_frac, q, mode, alpha, beta):
    prev_r1 = prev_top = None
    j_r1, j_top, s_r1, s_top, agree_r1, agree_top, lat = [], [], [], [], [], [], []
    for t in range(ticks):
        snap = book.step(t)
        static = snap["static"]
        X = static if mode == "baseline" else kinetic_transform(static, snap["delta"], alpha, beta)
        r1, top, ms = front_from_X(X, top_frac, q)
        lat.append(ms)
        r1f, topf, _ = front_from_X(static, top_frac, None)
        agree_r1.append(jaccard(r1, r1f)); agree_top.append(jaccard(top, topf))
        if prev_r1 is not None:
            j_r1.append(jaccard(prev_r1, r1)); j_top.append(jaccard(prev_top, top))
            s_r1.append(survival(prev_r1, r1)); s_top.append(survival(prev_top, top))
        prev_r1, prev_top = r1, top
    def med(xs): return float(np.median(xs)) if xs else 0.0
    return {"mode": mode, "jaccard_rank1": med(j_r1), "jaccard_top": med(j_top),
            "survival_rank1": med(s_r1), "survival_top": med(s_top),
            "agree_rank1_vs_full_static": med(agree_r1),
            "agree_top_vs_full_static": med(agree_top), "latency_ms": med(lat)}

def verdict(baseline, kinetic, min_agree):
    agree_ok = kinetic["agree_top_vs_full_static"] >= min_agree
    better = (kinetic["survival_top"] > baseline["survival_top"] + 1e-9 or
              kinetic["jaccard_top"] > baseline["jaccard_top"] + 1e-9)
    ship = bool(agree_ok and better)
    reason = ("SHIP: beats baseline durability with front agreement held" if ship else
              ("FAIL: front agreement vs full static collapsed" if not agree_ok else
               "FAIL: no durability improvement over baseline"))
    return {"ship": ship, "agree_ok": agree_ok, "better_durability": better, "reason": reason}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=int, default=100)
    ap.add_argument("--ticks", type=int, default=50)
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--sigma", type=float, default=0.15)
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--beta", type=float, default=0.5)
    ap.add_argument("--min-agree", type=float, default=0.90)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "docs" / "KINETIC_AB.json"))
    args = ap.parse_args()
    baseline = run_group(DriftBook(args.symbols, args.seed, args.sigma), args.ticks, args.top_frac, args.q, "baseline", args.alpha, args.beta)
    kinetic = run_group(DriftBook(args.symbols, args.seed, args.sigma), args.ticks, args.top_frac, args.q, "kinetic", args.alpha, args.beta)
    v = verdict(baseline, kinetic, args.min_agree)
    print(f"baseline J@top={baseline['jaccard_top']:.3f} S@top={baseline['survival_top']:.3f} agree={baseline['agree_top_vs_full_static']:.3f}")
    print(f"kinetic  J@top={kinetic['jaccard_top']:.3f} S@top={kinetic['survival_top']:.3f} agree={kinetic['agree_top_vs_full_static']:.3f}")
    print(f"verdict: {v['reason']}  ship={v['ship']}")
    payload = {"baseline": baseline, "kinetic": kinetic, "verdict": v,
               "params": vars(args), "scope": "A/B only. Not alpha. promote_ready=false."}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    md = out.with_suffix(".md")
    md.write_text(
        "# Kinetic A/B Match\n\n"
        f"| arm | J@top | S@top | agree@top |\n|:---|---:|---:|---:|\n"
        f"| baseline | {baseline['jaccard_top']:.3f} | {baseline['survival_top']:.3f} | {baseline['agree_top_vs_full_static']:.3f} |\n"
        f"| kinetic | {kinetic['jaccard_top']:.3f} | {kinetic['survival_top']:.3f} | {kinetic['agree_top_vs_full_static']:.3f} |\n\n"
        f"**Verdict:** {v['reason']} (`ship={v['ship']}`)\n\n"
        "Ship rule: agree@top ≥ min_agree AND (S@top or J@top) > baseline.\n\n"
        "`promote_ready=false`.\n"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
