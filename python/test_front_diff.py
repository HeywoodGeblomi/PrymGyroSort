#!/usr/bin/env python3
"""DOM-FD-001 acceptance: FD2 self-diff, FD3 fail-closed, book stayed-only."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "python" / "pair_sieve_cli.py"
VERIFY = ROOT / "python" / "verify_bundle.py"
DIFF = ROOT / "python" / "front_diff.py"
BOOK = ROOT / "examples" / "book.csv"
GYRO = ROOT / "cpp" / "include" / "gyro_rank.hpp"
GYRO_SHA = "e1b5433aa1113e90f761acccc6960736aedf3d07051474686f2380dd9a1ce080"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main() -> int:
    fails = []
    with tempfile.TemporaryDirectory(prefix="pgs_fd_") as td:
        td = Path(td)
        a = td / "a"
        b = td / "b"

        for dest in (a, b):
            r = run([
                sys.executable, str(CLI),
                "--csv", str(BOOK), "--x-col", "risk", "--y-col", "cost",
                "--bundle", str(dest),
            ])
            if r.returncode not in (0, 4):
                fails.append(f"seal failed for {dest.name}: {r.stderr or r.stdout}")
                print("FAIL:", fails[-1], file=sys.stderr)
                return 1

        r = run([sys.executable, str(DIFF), str(a), str(a), "--json"])
        if r.returncode != 0:
            fails.append(f"self-diff exit {r.returncode}: {r.stderr}")
        else:
            rep = json.loads(r.stdout)
            if rep["counts"]["entered"] != 0 or rep["counts"]["left"] != 0:
                fails.append(f"self-diff not stayed-only: {rep['counts']}")
            if rep["counts"]["stayed"] < 1:
                fails.append("self-diff stayed=0 unexpected")

        r = run([sys.executable, str(DIFF), str(a), str(b), "--json"])
        if r.returncode != 0:
            fails.append(f"identical diff exit {r.returncode}: {r.stderr}")
        else:
            rep = json.loads(r.stdout)
            if rep["counts"]["entered"] != 0 or rep["counts"]["left"] != 0:
                fails.append(f"identical seals not stayed-only: {rep['counts']}")

        bad = td / "bad"
        shutil.copytree(a, bad)
        with (bad / "front.csv").open("a") as f:
            f.write("tamper\n")
        r = run([sys.executable, str(DIFF), str(a), str(bad)])
        if r.returncode != 1:
            fails.append(f"bad bundle expected exit 1, got {r.returncode}")

        if GYRO.is_file():
            got = hashlib.sha256(GYRO.read_bytes()).hexdigest()
            if got != GYRO_SHA:
                fails.append(f"gyro_rank.hpp sha mismatch: {got}")
        else:
            fails.append("gyro_rank.hpp missing")

    if fails:
        for f in fails:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("FD acceptance GREEN (self-diff, identical, fail-closed, gyro)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
