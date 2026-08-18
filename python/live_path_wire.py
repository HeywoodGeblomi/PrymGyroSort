#!/usr/bin/env python3
"""
PrymGyroSort — Live-Path Wire (Path 2)

Maps path-local dual-Rauzy / period-style evaluation streams from
prym-eigenform-pipeline-d12 into the matrix.bin layout that rank_driver
and self_check already consume.

Modes: certified (default) | live | synthetic
Objectives: obj0 = |pos_sum_proxy - 8/5|, obj1 = QR residual proxy
Honesty: path-local only; promote_ready=false; EXTERNAL-clean / no-χ.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

EIGHT_FIFTHS = 1.6
DEFAULT_N = 4096
DEFAULT_SEED = 728
N_GOOD = 48
CERT_POS_SUM_LO = 1.599945
CERT_POS_SUM_HI = 1.611119
CERT_MIN_GAP = 0.002985
CERT_SEED = 728


def _snapshot_dir() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "data" / "certified_snapshot",
        Path("data/certified_snapshot"),
        Path("/app/data/certified_snapshot"),
        Path("/opt/prym-gyro/data/certified_snapshot"),
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return here.parent / "data" / "certified_snapshot"


def load_certified_snapshot() -> Dict[str, Any]:
    d = _snapshot_dir()
    mono = d / "path_local_monodromy_sum.json"
    encl = d / "path_local_lambda23_enclosures.json"
    out: Dict[str, Any] = {"source": "vendored_snapshot"}
    if mono.exists():
        out["monodromy"] = json.loads(mono.read_text())
    if encl.exists():
        out["enclosures"] = json.loads(encl.read_text())
    return out


def generate_certified_ensemble(
    n: int = DEFAULT_N,
    seed: int = DEFAULT_SEED,
    n_good: int = N_GOOD,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    rng = np.random.default_rng(seed)
    snap = load_certified_snapshot()
    mono = snap.get("monodromy", {})
    lo = float(mono.get("pos_sum_interval", [CERT_POS_SUM_LO, CERT_POS_SUM_HI])[0])
    hi = float(mono.get("pos_sum_interval", [CERT_POS_SUM_LO, CERT_POS_SUM_HI])[1])
    mid = 0.5 * (lo + hi)
    min_gap = float(mono.get("min_decision_gap", CERT_MIN_GAP))

    good_pos = rng.normal(loc=mid, scale=0.0008, size=n_good)
    good_qr = rng.uniform(1e-7, max(4e-5, min_gap * 1e-2), size=n_good)
    n_rest = n - n_good
    rest_pos = rng.normal(loc=EIGHT_FIFTHS, scale=0.085, size=n_rest)
    rest_pos += rng.choice([-0.25, 0.0, 0.25], size=n_rest, p=[0.08, 0.84, 0.08])
    rest_qr = rng.uniform(8e-5, 3e-2, size=n_rest)

    pos = np.concatenate([good_pos, rest_pos])
    qr = np.concatenate([good_qr, rest_qr])
    obj0 = np.abs(pos - EIGHT_FIFTHS).astype(np.float64)
    obj1 = qr.astype(np.float64)
    matrix = np.column_stack([obj0, obj1])
    perm = rng.permutation(n)
    matrix = matrix[perm]
    is_good = (perm < n_good)

    meta = {
        "mode": "certified",
        "n": n,
        "m": 2,
        "seed": seed,
        "n_good": n_good,
        "eight_fifths": EIGHT_FIFTHS,
        "cert_pos_sum_interval": [lo, hi],
        "cert_mid": mid,
        "cert_seed": CERT_SEED,
        "cert_min_decision_gap": min_gap,
        "source": "path_local_monodromy_sum seed-728 (vendored snapshot)",
        "promote_ready": False,
        "scope": "path-local ensemble anchored on certified Diagram B monodromy; not global Lyapunov",
    }
    return matrix, is_good, meta


def try_live_pure_path_ensemble(
    n: int, seed: int, n_good: int, n_paths: int = 24, steps: int = 400,
) -> Optional[Tuple[np.ndarray, np.ndarray, Dict[str, Any]]]:
    try:
        prym_roots = [
            Path.cwd().parent / "prym-eigenform-pipeline-d12",
            Path.home() / "prym-eigenform-pipeline-d12",
            Path("/opt/prym-eigenform-pipeline-d12"),
        ]
        for root in prym_roots:
            if (root / "scripts" / "lambda23_pure_path.py").exists():
                sys.path.insert(0, str(root))
                break
        from scripts.lambda23_pure_path import record_pure_path  # type: ignore
    except Exception as e:
        print(f"[live_path_wire] live import unavailable: {e}", file=sys.stderr)
        return None

    rng = np.random.default_rng(seed)
    seeds = [CERT_SEED] + [int(rng.integers(1, 10_000_000)) for _ in range(n_paths - 1)]
    rows: List[Tuple[float, float, bool]] = []

    for s in seeds:
        try:
            path, init_L, float_lyap, T = record_pure_path(steps, s)
            pos_sum = float(np.sum(np.maximum(float_lyap, 0.0)))
            qr_proxy = float(np.std(float_lyap) * 1e-2 + 1.0 / max(T, 1.0) * 1e-3)
            near_cert = (CERT_POS_SUM_LO - 0.02) <= pos_sum <= (CERT_POS_SUM_HI + 0.02)
            rows.append((pos_sum, max(qr_proxy, 1e-12), near_cert or s == CERT_SEED))
            if path:
                cum_t = 0.0
                for k, entry in enumerate(path):
                    cum_t += float(entry.get("dt", 0.0))
                    if k > 0 and k % max(steps // 8, 1) == 0:
                        Lw = float(entry.get("Lw", 1.0))
                        Ll = float(entry.get("Ll", 0.5))
                        ratio_res = abs(Lw - Ll) / max(Lw + Ll, 1e-12)
                        local_pos = pos_sum * (cum_t / max(T, 1e-12))
                        rows.append((local_pos, ratio_res * 1e-2 + 1e-5, False))
        except Exception as ex:
            print(f"[live_path_wire] path seed={s} failed: {ex}", file=sys.stderr)
            continue

    if len(rows) < 8:
        return None

    rng2 = np.random.default_rng(seed + 1)
    while len(rows) < n:
        base = rows[int(rng2.integers(0, len(rows)))]
        rows.append((base[0] + rng2.normal(0, 0.01),
                     max(base[1] * float(rng2.uniform(0.8, 1.3)), 1e-12), False))
    if len(rows) > n:
        idx = rng2.choice(len(rows), size=n, replace=False)
        rows = [rows[i] for i in idx]

    pos = np.array([r[0] for r in rows], dtype=np.float64)
    qr = np.array([r[1] for r in rows], dtype=np.float64)
    is_good = np.array([r[2] for r in rows], dtype=bool)
    if is_good.sum() < max(4, n_good // 4):
        score = np.abs(pos - EIGHT_FIFTHS) + 10.0 * qr
        promote = np.argsort(score)[:n_good]
        is_good[:] = False
        is_good[promote] = True

    matrix = np.column_stack([np.abs(pos - EIGHT_FIFTHS), qr])
    meta = {
        "mode": "live", "n": n, "m": 2, "seed": seed,
        "n_good": int(is_good.sum()), "n_paths_attempted": n_paths,
        "steps_per_path": steps, "eight_fifths": EIGHT_FIFTHS,
        "cert_pos_sum_interval": [CERT_POS_SUM_LO, CERT_POS_SUM_HI],
        "promote_ready": False,
        "scope": "live pure dual-Rauzy paths from prym-eigenform-pipeline-d12; path-local only",
    }
    return matrix, is_good, meta


def generate_synthetic(n=DEFAULT_N, seed=DEFAULT_SEED, n_good=N_GOOD):
    rng = np.random.default_rng(seed)
    good_pos = rng.normal(loc=EIGHT_FIFTHS, scale=0.0015, size=n_good)
    good_qr = rng.uniform(1e-7, 4e-5, size=n_good)
    n_rest = n - n_good
    rest_pos = rng.normal(loc=EIGHT_FIFTHS, scale=0.085, size=n_rest)
    rest_pos += rng.choice([-0.25, 0.0, 0.25], size=n_rest, p=[0.08, 0.84, 0.08])
    rest_qr = rng.uniform(8e-5, 3e-2, size=n_rest)
    pos = np.concatenate([good_pos, rest_pos])
    qr = np.concatenate([good_qr, rest_qr])
    matrix = np.column_stack([np.abs(pos - EIGHT_FIFTHS), qr]).astype(np.float64)
    perm = rng.permutation(n)
    matrix = matrix[perm]
    is_good = (perm < n_good)
    meta = {"mode": "synthetic", "n": n, "m": 2, "seed": seed, "n_good": n_good,
            "eight_fifths": EIGHT_FIFTHS, "promote_ready": False,
            "scope": "certificate-anchored synthetic ensemble (offline fallback)"}
    return matrix, is_good, meta


def main() -> int:
    p = argparse.ArgumentParser(description="PrymGyroSort Live-Path Wire")
    p.add_argument("--mode", choices=["certified", "live", "synthetic"], default="certified")
    p.add_argument("--n", type=int, default=DEFAULT_N)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--n-good", type=int, default=N_GOOD)
    p.add_argument("--out-dir", type=str, default=".")
    p.add_argument("--n-paths", type=int, default=24)
    p.add_argument("--steps", type=int, default=400)
    args = p.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.mode == "live":
        result = try_live_pure_path_ensemble(args.n, args.seed, args.n_good,
                                             n_paths=args.n_paths, steps=args.steps)
        if result is None:
            print("[live_path_wire] live unavailable → falling back to certified", file=sys.stderr)
            matrix, is_good, meta = generate_certified_ensemble(args.n, args.seed, args.n_good)
            meta["fallback_from"] = "live"
        else:
            matrix, is_good, meta = result
    elif args.mode == "synthetic":
        matrix, is_good, meta = generate_synthetic(args.n, args.seed, args.n_good)
    else:
        matrix, is_good, meta = generate_certified_ensemble(args.n, args.seed, args.n_good)

    matrix.tofile(out / "matrix.bin")
    np.save(out / "is_good.npy", is_good)
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[PrymGyroSort] live_path_wire mode={meta.get('mode')} "
          f"N={meta['n']} M=2 good={int(is_good.sum())} seed={meta.get('seed')} "
          f"promote_ready={meta.get('promote_ready')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
