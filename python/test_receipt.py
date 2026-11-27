#!/usr/bin/env python3
"""Receipt flag: stable except timestamp, book identity unchanged, tamper fails."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "python" / "pair_sieve_cli.py"
VERIFY = ROOT / "python" / "verify_receipt.py"
BOOK = ROOT / "examples" / "book.csv"
BOOK_IDENTITY = "968b5b2b85e9c402664f05a44b240ae657b70a57d56ef59e392cd567b12e0121"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def main() -> int:
    fails = []
    schema = json.loads((ROOT / "python" / "receipt.schema.json").read_text())
    if schema.get("properties", {}).get("schema_version", {}).get("const") != "1":
        fails.append("schema_version const")

    with tempfile.TemporaryDirectory(prefix="pgs_rcpt_") as td:
        td = Path(td)
        a = td / "a.json"
        b = td / "b.json"
        base = [
            sys.executable, str(CLI),
            "--csv", str(BOOK),
            "--x-col", "risk",
            "--y-col", "cost",
            "--x-sense", "lower",
            "--y-sense", "lower",
        ]
        plain = run(base)
        if plain.returncode != 0 or BOOK_IDENTITY not in plain.stdout:
            fails.append(f"plain book identity: {plain.returncode} {plain.stdout} {plain.stderr}")
        r1 = run(base + ["--receipt", str(a)])
        r2 = run(base + ["--receipt", str(b)])
        if r1.returncode != 0 or r2.returncode != 0:
            fails.append(f"receipt runs failed: {r1.stderr} {r2.stderr}")
        else:
            if BOOK_IDENTITY not in r1.stdout:
                fails.append("receipt run changed or dropped book identity")
            ja = json.loads(a.read_text())
            jb = json.loads(b.read_text())
            ja.pop("timestamp_utc", None)
            jb.pop("timestamp_utc", None)
            if ja != jb:
                fails.append("receipts differ aside from timestamp")
            if ja["output"]["identity_sha256"] != BOOK_IDENTITY:
                fails.append(f"receipt identity {ja['output']['identity_sha256']}")
            if ja["dominance_verification"]["method"] != "brute_force_weak_dominance":
                fails.append("book dominance method")
            if ja["dominance_verification"]["violations"] != 0:
                fails.append("book dominance violations")
            ok = run([sys.executable, str(VERIFY), str(a), "--csv", str(BOOK)])
            if ok.returncode != 0:
                fails.append(f"verifier rejected clean receipt: {ok.stderr}")
            ja_bad = json.loads(a.read_text())
            ja_bad["input"]["sha256"] = "0" * 64
            bad = td / "bad.json"
            bad.write_text(json.dumps(ja_bad) + "\n")
            bad_run = run([sys.executable, str(VERIFY), str(bad), "--csv", str(BOOK)])
            if bad_run.returncode == 0:
                fails.append("verifier accepted tampered input hash")

    if fails:
        for item in fails:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    print("GREEN: receipt self-check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
