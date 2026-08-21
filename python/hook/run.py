#!/usr/bin/env python3
"""GYR-HOOK-001 F1 — scheduler sidecar: options.csv → chosen.json.

Ranks an N_opt×2 talent menu via existing pair-sieve / prym_gyro (Fenwick oracle).
Does not write Photonic arrays. Does not edit gyro_rank.hpp.
promote_ready=false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

VERSION = "0.1.0-hook-f1"


def die(code: int, msg: str, *, as_json: bool = False) -> None:
    payload = {
        "ok": False,
        "error": msg,
        "exit_code": code,
        "version": VERSION,
        "promote_ready": False,
    }
    print(json.dumps(payload) if as_json else f"[hook] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def load_menu(path: Path):
    import csv as _csv

    if not path.is_file():
        die(2, f"menu not found: {path}")
    with path.open(newline="") as f:
        reader = _csv.DictReader(f)
        if not reader.fieldnames or "id" not in reader.fieldnames:
            die(2, "CSV must have header with id,score0,score1")
        fields = list(reader.fieldnames)
        for req in ("id", "score0", "score1"):
            if req not in fields:
                die(2, f"missing column {req!r}; have {fields}")
        rows = list(reader)
    if not rows:
        die(2, "menu empty")
    ids = []
    xs, ys = [], []
    for i, r in enumerate(rows):
        try:
            xv = float(r["score0"])
            yv = float(r["score1"])
        except (KeyError, TypeError, ValueError) as e:
            die(2, f"row {i}: {e}")
        if not (np.isfinite(xv) and np.isfinite(yv)):
            die(2, f"row {i}: non-finite")
        ids.append(str(r["id"]))
        xs.append(xv)
        ys.append(yv)
    X = np.ascontiguousarray(np.column_stack([xs, ys]), dtype=np.float64)
    return ids, X


def apply_senses(X: np.ndarray, x_sense: str, y_sense: str) -> np.ndarray:
    out = X.copy()
    if x_sense == "higher":
        out[:, 0] = -out[:, 0]
    if y_sense == "higher":
        out[:, 1] = -out[:, 1]
    return out


def run_falsifier(path: Path) -> dict:
    """Named H1: keep {A,B}, drop {G,H} under lower/lower."""
    ids, X = load_menu(path)
    from prym_gyro import rank, rank_fenwick_ref

    ranks = np.ascontiguousarray(rank(X, memory_pressure=False), dtype=np.int32)
    ranks_ref = np.ascontiguousarray(rank_fenwick_ref(X), dtype=np.int32)
    identity_ok = bool(np.array_equal(ranks, ranks_ref))
    F = {ids[i] for i in range(len(ids)) if ranks[i] == 1}
    keep = {"A", "B"}
    drop = {"G", "H"}
    keep_ok = keep.issubset(F)
    drop_ok = F.isdisjoint(drop)
    falsifier_ok = bool(identity_ok and keep_ok and drop_ok)
    return {
        "ok": falsifier_ok,
        "falsifier_ok": falsifier_ok,
        "keep_required": sorted(keep),
        "drop_required": sorted(drop),
        "front_ids": sorted(F),
        "identity_ok": identity_ok,
        "identity_mode": "fenwick_oracle",
        "promote_ready": False,
        "version": VERSION,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Hook scheduler sidecar {VERSION}")
    ap.add_argument("--csv", required=False, default=None, help="options.csv (id,score0,score1)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--x-sense", default="lower", choices=["lower", "higher"])
    ap.add_argument("--y-sense", default="lower", choices=["lower", "higher"])
    ap.add_argument("--chi", action="store_true", help="optional irreversible pick among F")
    ap.add_argument("--chi-seed", type=int, default=0)
    ap.add_argument("--falsifier", action="store_true", help="H1 fixture check")
    ap.add_argument("--out", default=None, help="write chosen.json here")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()
    as_json = bool(args.json)

    if args.version:
        print(json.dumps({"version": VERSION, "promote_ready": False}) if as_json else VERSION)
        return 0

    fixture = ROOT / "tests" / "fixtures" / "hook_menu.csv"

    if args.falsifier:
        path = Path(args.csv) if args.csv else fixture
        result = run_falsifier(path)
        print(json.dumps(result, indent=2) if as_json else result)
        return 0 if result["falsifier_ok"] else 9

    if not args.csv:
        die(1, "--csv required (or --falsifier)", as_json=as_json)

    ids, X = load_menu(Path(args.csv))
    X = apply_senses(X, args.x_sense, args.y_sense)

    from prym_gyro import rank, rank_fenwick_ref

    ranks = np.ascontiguousarray(rank(X, memory_pressure=False), dtype=np.int32)
    ranks_ref = np.ascontiguousarray(rank_fenwick_ref(X), dtype=np.int32)
    identity_ok = bool(np.array_equal(ranks, ranks_ref))
    sha = hashlib.sha256(ranks.tobytes()).hexdigest()
    front_idx = [i for i in range(len(ids)) if ranks[i] == 1]
    chosen_ids = [ids[i] for i in front_idx]
    front_size = len(chosen_ids)

    report = {
        "ok": True,
        "version": VERSION,
        "n": len(ids),
        "front_size": front_size,
        "chosen_ids": chosen_ids,
        "identity_ok": identity_ok,
        "identity_sha256": sha,
        "identity_mode": "fenwick_oracle",
        "strategy": "Fenwick2D",
        "promote_ready": False,
        "x_sense": args.x_sense,
        "y_sense": args.y_sense,
        "source": f"csv:{args.csv}",
    }

    if front_size == 0:
        die(2, "|F|==0 fail-closed: no undominated talent", as_json=as_json)

    if args.chi:
        from chi_pick import chi_pick

        F_idx = front_idx
        try:
            chi_result = chi_pick(F_idx, seed=args.chi_seed)
            pick_i = int(chi_result["pick"])
            if pick_i not in F_idx:
                die(4, f"chi pick index {pick_i} not in F", as_json=as_json)
            report.update(
                chi_on=True,
                chi_pick=ids[pick_i],
                chi_token=chi_result["chi_token"],
                chi_seed=int(args.chi_seed),
                chosen_id=ids[pick_i],
            )
        except ValueError as e:
            die(4, str(e), as_json=as_json)
    elif front_size == 1:
        report["chosen_id"] = chosen_ids[0]

    if as_json:
        print(json.dumps(report))
    else:
        print(
            f"[hook] n={report['n']} front_size={front_size} "
            f"chosen_ids={chosen_ids} identity_ok={identity_ok} "
            f"mode={report['identity_mode']} promote_ready=false"
        )

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))

    return 0 if identity_ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
