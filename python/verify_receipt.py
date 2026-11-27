#!/usr/bin/env python3
"""Re-check a run receipt against a CSV and the kernel file. Offline. Exit 0 or 1."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from receipt import verify_receipt  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-check a pair-sieve run receipt")
    ap.add_argument("receipt", help="receipt JSON path")
    ap.add_argument("--csv", default=None, help="input CSV to hash and, when present, re-rank")
    ap.add_argument("--repo", default=str(ROOT), help="repo root used to re-hash gyro_rank.hpp")
    ap.add_argument("--no-rerun", action="store_true", help="check hashes only")
    args = ap.parse_args()
    path = Path(args.receipt)
    try:
        receipt = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"receipt unreadable: {e}", file=sys.stderr)
        return 1
    fails = verify_receipt(
        receipt,
        csv_path=Path(args.csv) if args.csv else None,
        repo=Path(args.repo),
        rerun=not args.no_rerun,
    )
    if fails:
        for item in fails:
            print(item, file=sys.stderr)
        return 1
    print("receipt ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
