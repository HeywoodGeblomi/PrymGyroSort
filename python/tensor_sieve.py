#!/usr/bin/env python3
"""M=3 tensor sieve lab — exact 3-D Python ranks vs static/dynamic quantile. No rank_m3. promote_ready=false."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def exact_rank_3d(X):
    n = X.shape[0]
    if n == 0: return np.zeros(0, dtype=np.int32)
    remaining = np.ones(n, dtype=bool)
    ranks = np.zeros(n, dtype=np.int32)
    layer = 1
    while remaining.any():
        idx = np.flatnonzero(remaining)
        pts = X[idx]
        dominated = np.zeros(len(idx), dtype=bool)
        for a in range(len(idx)):
            ge = (pts <= pts[a]).all(axis=1); strict = (pts < pts[a]).any(axis=1)
            ge[a] = False
            if np.any(ge & strict): dominated[a] = True
        front = idx[~dominated]
        if front.size == 0:
            ranks[idx] = layer; break
        ranks[front] = layer; remaining[front] = False; layer += 1
        if layer > n + 1: break
    return ranks

def make_ensemble_m3(n, seed, n_good=64):
    rng = np.random.default_rng(seed)
    X = rng.random((n, 3))
    k = min(n_good, n)
    idx = rng.choice(n, size=k, replace=False)
    X[idx] = rng.uniform(0.0, 0.08, size=(k, 3))
    return np.ascontiguousarray(X, dtype=np.float64)

def static_quantile_mask(X, q):
    n = X.shape[0]; k = max(1, int(np.ceil(q * n))); keep = np.zeros(n, dtype=bool)
    for d in range(X.shape[1]):
        t = np.partition(X[:, d], k - 1)[k - 1]; keep |= X[:, d] <= t
    return keep

def dynamic_quantile_mask(X, baseline_q=0.25):
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.corrcoef(X.T)
    if not np.isfinite(corr).all(): avg_abs = 0.0
    else:
        iu = np.triu_indices(X.shape[1], k=1)
        avg_abs = float(np.mean(np.abs(corr[iu])))
    dynamic_q = float(np.clip(baseline_q + (1.0 - avg_abs) * 0.15, 0.15, 0.45))
    return static_quantile_mask(X, dynamic_q), dynamic_q

def top_frac_idx(ranks, frac):
    return np.argsort(ranks, kind="stable")[: max(1, int(frac * ranks.shape[0]))]

def rank1_idx(ranks):
    return np.flatnonzero(ranks == ranks.min())

def recall(true_idx, pred_idx):
    return 1.0 if true_idx.size == 0 else float(np.isin(true_idx, pred_idx).mean())

def run_once(X, mode, q, top_frac):
    n = X.shape[0]
    t0 = time.perf_counter(); ranks_full = exact_rank_3d(X); t_full = (time.perf_counter() - t0) * 1e3
    true_r1, true_top = rank1_idx(ranks_full), top_frac_idx(ranks_full, top_frac)
    t1 = time.perf_counter()
    if mode == "static": keep, used_q = static_quantile_mask(X, q), q
    else: keep, used_q = dynamic_quantile_mask(X, baseline_q=q)
    t_filt = (time.perf_counter() - t1) * 1e3
    idx = np.flatnonzero(keep); Xp = X[idx]
    t2 = time.perf_counter(); ranks_p = exact_rank_3d(Xp); t_rank = (time.perf_counter() - t2) * 1e3
    order = np.argsort(ranks_p, kind="stable")
    pred_top = idx[order[: max(1, int(top_frac * n))]]
    pred_r1 = idx[ranks_p == ranks_p.min()]
    return {"n": n, "mode": mode, "used_q": used_q, "n_prime": int(idx.size), "keep_frac": float(idx.size / n),
            "t_full_ms": t_full, "t_pipeline_ms": t_filt + t_rank,
            "speedup": t_full / (t_filt + t_rank) if (t_filt + t_rank) > 0 else 0.0,
            "recall_rank1": recall(true_r1, pred_r1), "recall_top_frac": recall(true_top, pred_top)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ladder", default="400,800,1200")
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--out", default=str(ROOT / "docs" / "TENSOR_SIEVE_M3.json"))
    args = ap.parse_args()
    sizes = [int(x) for x in args.ladder.split(",") if x.strip()]
    print("[tensor-m3] exact 3-D vs static/dynamic quantile")
    rows = []
    for n in sizes:
        X = make_ensemble_m3(n, args.seed)
        for mode in ("static", "dynamic"):
            samples = [run_once(X, mode, args.q, args.top_frac) for _ in range(args.reps)]
            def med(k): return float(np.median([s[k] for s in samples]))
            rec = {"n": n, "mode": mode, "used_q": med("used_q"), "keep_frac": med("keep_frac"),
                   "n_prime": int(med("n_prime")), "t_pipeline_ms": med("t_pipeline_ms"),
                   "t_full_ms": med("t_full_ms"), "speedup": med("speedup"),
                   "recall_rank1": med("recall_rank1"), "recall_top_frac": med("recall_top_frac")}
            rows.append(rec)
            print(f"N={n} {mode} q={rec['used_q']:.3f} keep={100*rec['keep_frac']:.1f}% "
                  f"spd={rec['speedup']:.2f} R1={rec['recall_rank1']:.2f} Rtop={rec['recall_top_frac']:.2f}")
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": rows, "scope": "lab only; no rank_m3; kernel M=2; promote_ready=false"}, indent=2))
    md = out.with_suffix(".md")
    lines = ["# M=3 Tensor Sieve (honest lab)", "",
             "| N | mode | q | keep% | speedup | R@1 | R@top |", "|---:|:---|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['n']} | {r['mode']} | {r['used_q']:.3f} | {100*r['keep_frac']:.1f}% | "
                     f"{r['speedup']:.2f} | {r['recall_rank1']:.2f} | {r['recall_top_frac']:.2f} |")
    lines += ["", "No `rank_m3`. Kernel remains M=2. `promote_ready=false`.", ""]
    md.write_text("\n".join(lines))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
