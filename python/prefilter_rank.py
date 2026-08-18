#!/usr/bin/env python3
"""Coarse pre-filter approximate sieve + recall-vs-latency profiler. promote_ready=false."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from prym_gyro import rank  # noqa: E402

def make_ensemble(n, seed, n_good=48):
    rng = np.random.default_rng(seed)
    obj0, obj1 = rng.random(n), rng.random(n)
    k = min(n_good, n)
    idx = rng.choice(n, size=k, replace=False)
    obj0[idx] = rng.uniform(0.0, 0.08, size=k)
    obj1[idx] = rng.uniform(0.0, 0.08, size=k)
    X = np.ascontiguousarray(np.column_stack([obj0, obj1]), dtype=np.float64)
    return X

def filter_quantile(X, q):
    n = X.shape[0]
    k = max(1, int(np.ceil(q * n)))
    t0 = np.partition(X[:, 0], k - 1)[k - 1]
    t1 = np.partition(X[:, 1], k - 1)[k - 1]
    return (X[:, 0] <= t0) | (X[:, 1] <= t1)

def filter_anchor(X, n_anchors, seed):
    n = X.shape[0]
    rng = np.random.default_rng(seed)
    anchors = {int(np.argmin(X[:, 0])), int(np.argmin(X[:, 1])), int(np.argmin(X[:, 0] + X[:, 1]))}
    while len(anchors) < min(n_anchors, n):
        anchors.add(int(rng.integers(0, n)))
    anchors = list(anchors)
    A = X[anchors]
    keep = np.ones(n, dtype=bool)
    for i in range(n):
        if i in anchors:
            continue
        dom = np.any((A[:, 0] <= X[i, 0]) & (A[:, 1] <= X[i, 1]) &
                     ((A[:, 0] < X[i, 0]) | (A[:, 1] < X[i, 1])))
        if dom:
            keep[i] = False
    return keep

def top_frac_indices(ranks, frac):
    k = max(1, int(frac * ranks.shape[0]))
    return np.argsort(ranks, kind="stable")[:k]

def rank1_indices(ranks):
    return np.flatnonzero(ranks == ranks.min())

def recall(true_idx, pred_idx):
    if true_idx.size == 0:
        return 1.0
    return float(np.isin(true_idx, pred_idx).mean())

def run_once(X, method, q, n_anchors, top_frac, seed):
    n = X.shape[0]
    t0 = time.perf_counter()
    ranks_full = rank(X, memory_pressure=False)
    t_full = (time.perf_counter() - t0) * 1e3
    true_r1 = rank1_indices(ranks_full)
    true_top = top_frac_indices(ranks_full, top_frac)
    t1 = time.perf_counter()
    if method == "quantile":
        keep = filter_quantile(X, q)
    else:
        keep = filter_anchor(X, n_anchors, seed)
    t_filt = (time.perf_counter() - t1) * 1e3
    idx = np.flatnonzero(keep)
    Xp = np.ascontiguousarray(X[idx], dtype=np.float64)
    t2 = time.perf_counter()
    ranks_p = rank(Xp, memory_pressure=False)
    t_rank = (time.perf_counter() - t2) * 1e3
    t_total = t_filt + t_rank
    order_p = np.argsort(ranks_p, kind="stable")
    pred_top = idx[order_p[: max(1, int(top_frac * n))]]
    pred_r1 = idx[ranks_p == ranks_p.min()]
    return {"n": n, "n_prime": int(idx.size), "keep_frac": idx.size / n, "method": method,
            "t_full_ms": t_full, "t_pipeline_ms": t_total,
            "speedup_vs_full": t_full / t_total if t_total > 0 else 0.0,
            "recall_rank1": recall(true_r1, pred_r1), "recall_top_frac": recall(true_top, pred_top)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ladder", default="1024,6400,12800,32000")
    ap.add_argument("--method", default="both", choices=["quantile", "anchor", "both"])
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--n-anchors", type=int, default=16)
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--out", default=str(ROOT / "docs" / "PREFILTER_RECALL.json"))
    args = ap.parse_args()
    sizes = [int(x) for x in args.ladder.split(",") if x.strip()]
    methods = ["quantile", "anchor"] if args.method == "both" else [args.method]
    print("[prefilter] approximate sieve — latency + front recall")
    rows = []
    for n in sizes:
        X = make_ensemble(n, args.seed)
        for method in methods:
            samples = [run_once(X, method, args.q, args.n_anchors, args.top_frac, args.seed + r)
                       for r in range(args.reps)]
            def med(k): return float(np.median([s[k] for s in samples]))
            rec = {"n": n, "method": method, "n_prime": int(med("n_prime")), "keep_frac": med("keep_frac"),
                   "t_pipeline_ms": med("t_pipeline_ms"), "t_full_ms": med("t_full_ms"),
                   "speedup_vs_full": med("speedup_vs_full"),
                   "recall_rank1": med("recall_rank1"), "recall_top_frac": med("recall_top_frac")}
            rows.append(rec)
            print(f"{n:7d} {method:>9} N'={rec['n_prime']:7d} keep={100*rec['keep_frac']:5.1f}% "
                  f"pipe={rec['t_pipeline_ms']:7.2f}ms full={rec['t_full_ms']:7.2f}ms "
                  f"spd={rec['speedup_vs_full']:5.2f} R1={rec['recall_rank1']:.2f} Rtop={rec['recall_top_frac']:.2f}")
    payload = {"results": rows, "scope": "APPROXIMATE sieve only; promote_ready=false"}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    md = out.with_suffix(".md")
    lines = ["# Coarse Pre-Filter: Latency vs Front Recall", "",
             "| N | method | N' | keep% | pipeline ms | full ms | speedup | R@rank1 | R@top-frac |",
             "|---:|:---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['n']} | {r['method']} | {r['n_prime']} | {100*r['keep_frac']:.1f}% | "
                     f"{r['t_pipeline_ms']:.2f} | {r['t_full_ms']:.2f} | {r['speedup_vs_full']:.2f} | "
                     f"{r['recall_rank1']:.2f} | {r['recall_top_frac']:.2f} |")
    lines += ["", "Quantile SHIPS (R=1.0, ~2.5×). Anchor KILLED (R@top collapses, slower).", "",
              "`promote_ready=false` — approximate sieve only.", ""]
    md.write_text("\n".join(lines))
    print(f"[prefilter] wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
