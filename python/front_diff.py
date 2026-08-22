#!/usr/bin/env python3
"""DOM-FD-001 — Front Diff: two seals → entered / left / stayed.

Diff only. Not a re-rank. Not a forecast.
Both inputs must pass verify_bundle first; either fails → exit 1, no diff.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

VERSION = "0.1.0-front-diff"
ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "python" / "verify_bundle.py"

# Columns never used as identity material
EXCLUDE_COLS = frozenset({"rank", "chi_pick"})
ID_CANDIDATES = ("idx", "id", "index", "row")


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def run_verify(dir_path: Path) -> int:
    """Return verify_bundle exit code."""
    if not VERIFY.is_file():
        die(f"verify_bundle not found: {VERIFY}")
    r = subprocess.run(
        [sys.executable, str(VERIFY), str(dir_path)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 and r.stderr:
        print(r.stderr.strip(), file=sys.stderr)
    return r.returncode


def load_report(dir_path: Path) -> Dict[str, Any]:
    p = dir_path / "report.json"
    if not p.is_file():
        die(f"missing report.json in {dir_path}")
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        die(f"report.json unreadable in {dir_path}: {e}")


def row_identity_key(row: Dict[str, str], fields: List[str]) -> str:
    """Prefer explicit id column; else stable hash of non-excluded cells."""
    for cand in ID_CANDIDATES:
        if cand in fields and cand in row:
            val = row[cand]
            if val is not None and str(val).strip() != "":
                return str(val).strip()
    # Stable hash of remaining cells
    parts = []
    for f in sorted(fields):
        if f in EXCLUDE_COLS or f in ID_CANDIDATES:
            continue
        parts.append(f"{f}={row.get(f, '')}")
    material = "|".join(parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def load_front_keys(dir_path: Path) -> Tuple[Set[str], List[str]]:
    """Return (set of identity keys, ordered list of keys as they appear)."""
    front = dir_path / "front.csv"
    if not front.is_file():
        die(f"missing front.csv in {dir_path}")
    keys: Set[str] = set()
    ordered: List[str] = []
    with front.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return keys, ordered
        fields = list(reader.fieldnames)
        for row in reader:
            k = row_identity_key(row, fields)
            if k not in keys:
                ordered.append(k)
            keys.add(k)
    return keys, ordered


def front_diff(dir_a: Path, dir_b: Path) -> Dict[str, Any]:
    # Fail closed: both must verify
    if run_verify(dir_a) != 0:
        die(f"verify failed for A: {dir_a}")
    if run_verify(dir_b) != 0:
        die(f"verify failed for B: {dir_b}")

    keys_a, _ = load_front_keys(dir_a)
    keys_b, _ = load_front_keys(dir_b)

    entered = sorted(keys_b - keys_a)
    left = sorted(keys_a - keys_b)
    stayed = sorted(keys_a & keys_b)

    rep_a = load_report(dir_a)
    rep_b = load_report(dir_b)

    out: Dict[str, Any] = {
        "ok": True,
        "version": VERSION,
        "n_a": len(keys_a),
        "n_b": len(keys_b),
        "counts": {
            "entered": len(entered),
            "left": len(left),
            "stayed": len(stayed),
        },
        "entered": entered,
        "left": left,
        "stayed": stayed,
        "identity_sha256_a": rep_a.get("identity_sha256"),
        "identity_sha256_b": rep_b.get("identity_sha256"),
        "score_contract_hash_a": rep_a.get("score_contract_hash"),
        "score_contract_hash_b": rep_b.get("score_contract_hash"),
    }
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="DOM-FD-001 Front Diff: two verified seals → entered / left / stayed"
    )
    ap.add_argument("dir_a", type=Path, help="bundle directory A")
    ap.add_argument("dir_b", type=Path, help="bundle directory B")
    ap.add_argument("--json", action="store_true", help="print full JSON report")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args(argv)

    if args.version:
        print(VERSION)
        return 0

    if not args.dir_a.is_dir():
        die(f"not a directory: {args.dir_a}")
    if not args.dir_b.is_dir():
        die(f"not a directory: {args.dir_b}")

    result = front_diff(args.dir_a, args.dir_b)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        c = result["counts"]
        print(
            f"[front_diff] entered={c['entered']} left={c['left']} stayed={c['stayed']} "
            f"n_a={result['n_a']} n_b={result['n_b']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
