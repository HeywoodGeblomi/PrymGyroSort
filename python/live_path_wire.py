#!/usr/bin/env python3
"""
PrymGyroSort Path-2 live wire — stream path-local dual-Rauzy / KZ snapshots
from prym-eigenform-pipeline-d12 into the rank_driver matrix.bin contract.

Modes:
  --mode live       : require prym checkout on PYTHONPATH; use code.integrator.run
  --mode auto       : try live, fall back to synthetic (default)
  --mode synthetic  : certificate-anchored synthetic (CI / offline fallback)

Contract (unchanged):
  matrix.bin   : float64 row-major N x 2  (obj0, obj1)
  is_good.npy  : bool[N]
  meta.json    : provenance

Objectives (lower better):
  obj0 = |pos_sum_proxy - 8/5|
  obj1 = QR / spectrum-shape residual proxy

Honesty: path-local only. promote_ready stays false. EXTERNAL-clean / no-χ.
Does not claim global Lyapunov exponents or ownership of 8/5 (Chen–Möller).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

EIGHT_FIFTHS = 1.6
SUM23_TARGET = 0.6
DEFAULT_N = 4096
DEFAULT_SEED = 728
N_GOOD_DEFAULT = 48

CERT_POS_SUM_LO = 1.599945
CERT_POS_SUM_HI = 1.611119


def _synthetic_ensemble(
    n: int, seed: int, n_good: int
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    rng = np.random.default_rng(seed)
    good_pos = rng.normal(loc=EIGHT_FIFTHS, scale=0.0015, size=n_good)
    good_qr = rng.uniform(1e-7, 4e-5, size=n_good)
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
    is_good = perm < n_good
    meta = {
        "mode": "synthetic",
        "n": n,
        "m": 2,
        "seed": seed,
        "n_good": n_good,
        "eight_fifths": EIGHT_FIFTHS,
        "promote_ready": False,
        "scope": "certificate-anchored synthetic; path-local self-check only",
    }
    return matrix, is_good, meta


def _try_import_prym_integrator():
    try:
        from code.integrator import run as prym_run  # type: ignore
        return prym_run
    except Exception:
        pass
    import os
    root = os.environ.get("PRYM_ROOT")
    if root:
        sys.path.insert(0, root)
        try:
            from code.integrator import run as prym_run  # type: ignore
            return prym_run
        except Exception:
            pass
    return None


def _snapshot_to_objectives(lyap: List[float]) -> Tuple[float, float]:
    arr = np.asarray(lyap, dtype=np.float64)
    pos_sum = float(np.sum(arr[arr > 0.0])) if arr.size else 0.0
    obj0 = abs(pos_sum - EIGHT_FIFTHS)
    if arr.size >= 3:
        sum23 = float(arr[1] + arr[2])
        obj1 = abs(sum23 - SUM23_TARGET) + 0.05 * abs(float(arr[0]) - 1.0)
    else:
        obj1 = abs(pos_sum - EIGHT_FIFTHS) + 0.1
    obj1 = max(obj1, 1e-12)
    return obj0, obj1


def _live_ensemble(
    n: int,
    seed: int,
    n_good: int,
    n_steps: int,
    reorth_every: int,
    prym_run,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    rng = np.random.default_rng(seed)
    seeds = [728]
    extra = max(1, (n // max(1, n_steps // reorth_every)) + 4)
    for i in range(extra * 3):
        s = int(rng.integers(1, 10_000_000))
        if s not in seeds:
            seeds.append(s)
        if len(seeds) >= extra + 1:
            break

    rows: List[Tuple[float, float, bool, int, int]] = []
    for s in seeds:
        try:
            snaps = prym_run(n_steps=n_steps, reorth_every=reorth_every, seed=s)
        except Exception as e:
            print(f"[live_path_wire] integrator seed={s} failed: {e}", file=sys.stderr)
            continue
        for snap in snaps:
            lyap = snap.get("lyap") or []
            obj0, obj1 = _snapshot_to_objectives(lyap)
            arr = np.asarray(lyap, dtype=np.float64)
            pos_sum_est = float(np.sum(arr[arr > 0.0])) if arr.size else 0.0
            in_cert_band = CERT_POS_SUM_LO <= pos_sum_est <= CERT_POS_SUM_HI
            low_shape = obj1 < 0.08
            is_anchor = (s == 728 and in_cert_band) or (in_cert_band and low_shape)
            rows.append((obj0, obj1, bool(is_anchor), s, int(snap.get("step", 0))))

    if not rows:
        raise RuntimeError("live integrator produced zero snapshots; check PRYM_ROOT / PYTHONPATH")

    rows.sort(key=lambda r: (r[0], r[1]))
    anchors = [r for r in rows if r[2]]
    take_good = anchors[:n_good] if anchors else rows[:n_good]
    selected: List[Tuple[float, float, bool, int, int]] = []
    for r in take_good:
        selected.append((r[0], r[1], True, r[3], r[4]))
    remaining = [r for r in rows if r not in take_good]
    need = n - len(selected)
    for r in remaining[: max(0, need)]:
        selected.append((r[0], r[1], False, r[3], r[4]))

    while len(selected) < n:
        base = rows[len(selected) % len(rows)]
        jitter0 = float(rng.normal(0, 1e-4))
        jitter1 = float(abs(rng.normal(0, 1e-5)))
        selected.append(
            (max(0.0, base[0] + jitter0), max(1e-12, base[1] + jitter1), False, base[3], base[4])
        )

    selected = selected[:n]
    rng.shuffle(selected)

    matrix = np.array([[o0, o1] for o0, o1, _, _, _ in selected], dtype=np.float64)
    is_good = np.array([g for _, _, g, _, _ in selected], dtype=bool)
    if not is_good.any() and n_good > 0:
        order = np.argsort(matrix[:, 0])
        is_good[order[:n_good]] = True

    meta = {
        "mode": "live",
        "n": n,
        "m": 2,
        "seed": seed,
        "n_good": int(is_good.sum()),
        "n_good_requested": n_good,
        "n_steps": n_steps,
        "reorth_every": reorth_every,
        "eight_fifths": EIGHT_FIFTHS,
        "sum23_target": SUM23_TARGET,
        "cert_pos_sum_interval": [CERT_POS_SUM_LO, CERT_POS_SUM_HI],
        "n_integrator_seeds": len(seeds),
        "n_raw_snapshots": len(rows),
        "promote_ready": False,
        "scope": (
            "LIVE path-local KZ snapshots from prym-eigenform-pipeline-d12 "
            "code.integrator.run. Path-local only; not global Lyapunov spectrum. "
            "Does not claim ownership of 8/5."
        ),
        "source": "prym-eigenform-pipeline-d12 / code.integrator",
    }
    return matrix, is_good, meta


def generate(
    n: int = DEFAULT_N,
    seed: int = DEFAULT_SEED,
    n_good: int = N_GOOD_DEFAULT,
    mode: str = "auto",
    n_steps: int = 4000,
    reorth_every: int = 200,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    mode = mode.lower().strip()
    if mode not in ("auto", "live", "synthetic"):
        raise ValueError(f"unknown mode {mode}")

    if mode == "synthetic":
        return _synthetic_ensemble(n, seed, n_good)

    prym_run = _try_import_prym_integrator()
    if prym_run is None:
        if mode == "live":
            raise RuntimeError(
                "live mode requires prym-eigenform-pipeline-d12 on PYTHONPATH "
                "or PRYM_ROOT (code.integrator.run). Import failed."
            )
        print(
            "[live_path_wire] prym integrator unavailable — falling back to synthetic",
            file=sys.stderr,
        )
        return _synthetic_ensemble(n, seed, n_good)

    try:
        return _live_ensemble(n, seed, n_good, n_steps, reorth_every, prym_run)
    except Exception as e:
        if mode == "live":
            raise
        print(f"[live_path_wire] live ensemble failed ({e}); synthetic fallback", file=sys.stderr)
        return _synthetic_ensemble(n, seed, n_good)


def main() -> int:
    p = argparse.ArgumentParser(description="PrymGyroSort Path-2 live wire / matrix generator")
    p.add_argument("--n", type=int, default=DEFAULT_N)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--n-good", type=int, default=N_GOOD_DEFAULT)
    p.add_argument("--out-dir", type=str, default=".")
    p.add_argument(
        "--mode",
        choices=("auto", "live", "synthetic"),
        default="auto",
        help="auto=try live then synthetic; live=require prym; synthetic=offline fallback",
    )
    p.add_argument("--n-steps", type=int, default=4000, help="KZ steps per live path")
    p.add_argument("--reorth-every", type=int, default=200, help="snapshot interval")
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    matrix, is_good, meta = generate(
        n=args.n,
        seed=args.seed,
        n_good=args.n_good,
        mode=args.mode,
        n_steps=args.n_steps,
        reorth_every=args.reorth_every,
    )
    matrix.tofile(out / "matrix.bin")
    np.save(out / "is_good.npy", is_good)
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        f"[PrymGyroSort] live_path_wire mode={meta['mode']} "
        f"N={meta['n']} M=2 good={int(is_good.sum())} seed={meta['seed']} "
        f"promote_ready={meta['promote_ready']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
