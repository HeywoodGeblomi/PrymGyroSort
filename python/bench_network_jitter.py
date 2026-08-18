#!/usr/bin/env python3
"""Network jitter / OOO frame simulation vs clean delivery. promote_ready=false."""
from __future__ import annotations
import argparse, json, sys
from collections import deque
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from frontier_durability import jaccard, survival  # noqa: E402
from prefilter_rank import filter_quantile  # noqa: E402
from prym_gyro import rank  # noqa: E402
from test_kinetic_match import DriftBook  # noqa: E402

def front_q(X, top_frac, q):
    n = X.shape[0]
    keep = filter_quantile(X, q)
    idx = np.flatnonzero(keep)
    ranks = rank(np.ascontiguousarray(X[idx]), memory_pressure=False)
    order = np.argsort(ranks, kind="stable")
    top = idx[order[: max(1, int(top_frac * n))]]
    r1 = idx[ranks == ranks.min()]
    return r1, top

def deliver_frames(frames, mode, rng, drop_p, delay):
    n = len(frames)
    if mode == "clean": return list(frames)
    if mode == "drop":
        out = [f for f in frames if rng.random() > drop_p]
        return out if out else [frames[0]]
    if mode == "reorder":
        out, i = [], 0
        while i < n:
            w = frames[i:i+5]; idx = np.arange(len(w)); rng.shuffle(idx)
            out.extend(w[j] for j in idx); i += 5
        return out
    if mode == "delay":
        buf, out = deque(), []
        for f in frames:
            buf.append(f)
            if len(buf) > delay: out.append(buf.popleft())
        while buf: out.append(buf.popleft())
        return out
    if mode == "burst":
        out, buf = [], []
        for i, f in enumerate(frames):
            buf.append(f)
            if (i + 1) % 4 == 0: out.extend(buf); buf = []
        out.extend(buf); return out
    raise ValueError(mode)

def score_delivery(delivered, top_frac, q):
    prev_top = None
    j_top, s_top = [], []
    for X in delivered:
        _, top = front_q(X, top_frac, q)
        if prev_top is not None:
            j_top.append(jaccard(prev_top, top)); s_top.append(survival(prev_top, top))
        prev_top = top
    def med(xs): return float(np.median(xs)) if xs else 0.0
    return {"jaccard_top": med(j_top), "survival_top": med(s_top), "n_delivered": len(delivered)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=int, default=100)
    ap.add_argument("--ticks", type=int, default=60)
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--sigma", type=float, default=0.15)
    ap.add_argument("--drop-p", type=float, default=0.15)
    ap.add_argument("--delay", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "docs" / "NETWORK_JITTER.json"))
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    book = DriftBook(args.symbols, args.seed, args.sigma)
    frames = [book.step(t)["static"] for t in range(args.ticks)]
    results = {}
    for mode in ["clean", "drop", "reorder", "delay", "burst"]:
        delivered = deliver_frames(frames, mode, rng, args.drop_p, args.delay)
        sc = score_delivery(delivered, args.top_frac, args.q)
        if mode != "clean":
            sc["delta_jaccard_top"] = abs(sc["jaccard_top"] - results["clean"]["jaccard_top"])
            sc["delta_survival_top"] = abs(sc["survival_top"] - results["clean"]["survival_top"])
        results[mode] = sc
        print(f"{mode:>10} n={sc['n_delivered']} J@top={sc['jaccard_top']:.3f} S@top={sc['survival_top']:.3f}")
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results, "scope": "simulation only; promote_ready=false"}, indent=2))
    md = out.with_suffix(".md")
    lines = ["# Network Jitter Resilience", "",
             "| mode | n | J@top | S@top | ΔJ | ΔS |", "|:---|---:|---:|---:|---:|---:|"]
    for mode, sc in results.items():
        lines.append(f"| {mode} | {sc['n_delivered']} | {sc['jaccard_top']:.3f} | {sc['survival_top']:.3f} | "
                     f"{sc.get('delta_jaccard_top', 0):.3f} | {sc.get('delta_survival_top', 0):.3f} |")
    lines += ["", "Simulation only. `promote_ready=false`.", ""]
    md.write_text("\n".join(lines))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
