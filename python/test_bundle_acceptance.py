#!/usr/bin/env python3
"""PGS-BUN / DOM-SC-001 acceptance: B1–B6. No kernel."""
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
BOOK = ROOT / "examples" / "book.csv"
GYRO = ROOT / "cpp" / "include" / "gyro_rank.hpp"
GYRO_SHA = "e1b5433aa1113e90f761acccc6960736aedf3d07051474686f2380dd9a1ce080"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main() -> int:
    fails = []
    with tempfile.TemporaryDirectory(prefix="pgs_bun_") as td:
        td = Path(td)
        clean = td / "clean"
        r = run(
            [
                sys.executable,
                str(CLI),
                "--csv",
                str(BOOK),
                "--x-col",
                "risk",
                "--y-col",
                "cost",
                "--bundle",
                str(clean),
            ]
        )
        if r.returncode not in (0, 4):
            fails.append(f"B1 sieve failed: {r.stderr or r.stdout}")
        else:
            for name in ("front.csv", "report.json", "MANIFEST.sha256"):
                if not (clean / name).is_file():
                    fails.append(f"B1 missing {name}")
            v = run([sys.executable, str(VERIFY), str(clean)])
            if v.returncode != 0:
                fails.append(f"B2 verify clean failed: {v.stderr.strip()}")

        chi_dir = td / "chi"
        r = run(
            [
                sys.executable,
                str(CLI),
                "--csv",
                str(BOOK),
                "--x-col",
                "risk",
                "--y-col",
                "cost",
                "--chi",
                "--bundle",
                str(chi_dir),
            ]
        )
        if r.returncode not in (0, 4):
            fails.append(f"B3 setup sieve failed: {r.stderr or r.stdout}")
        else:
            rep = json.loads((chi_dir / "report.json").read_text())
            if not rep.get("chi_on") or "r_chi=" not in str(rep.get("chi_token", "")):
                fails.append("B3 setup: expected chi_on + r_chi= token")
            else:
                rep["chi_token"] = "hash_only_rejected"
                (chi_dir / "report.json").write_text(json.dumps(rep, indent=2) + "\n")
                lines = []
                for name in ("front.csv", "report.json"):
                    h = hashlib.sha256((chi_dir / name).read_bytes()).hexdigest()
                    lines.append(f"{h}  {name}")
                (chi_dir / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
                v = run([sys.executable, str(VERIFY), str(chi_dir)])
                if v.returncode != 1:
                    fails.append(f"B3 expected exit 1 for hash-only, got {v.returncode}")

        tamp = td / "tamp"
        shutil.copytree(clean, tamp)
        with (tamp / "front.csv").open("a") as f:
            f.write("tamper\n")
        v = run([sys.executable, str(VERIFY), str(tamp)])
        if v.returncode != 1:
            fails.append(f"B4 expected exit 1 for tamper, got {v.returncode}")

        if GYRO.is_file():
            got = hashlib.sha256(GYRO.read_bytes()).hexdigest()
            if got != GYRO_SHA:
                fails.append(f"B5 gyro_rank.hpp sha mismatch: {got}")
        else:
            fails.append("B5 gyro_rank.hpp missing")

        # B6: score_contract_hash mismatch → verify exit 1
        sc_dir = td / "sc_bad"
        shutil.copytree(clean, sc_dir)
        rep = json.loads((sc_dir / "report.json").read_text())
        if "score_contract" in rep and "score_contract_hash" in rep:
            rep["score_contract_hash"] = "0" * 64
            (sc_dir / "report.json").write_text(json.dumps(rep, indent=2) + "\n")
            lines = []
            for name in ("front.csv", "report.json"):
                h = hashlib.sha256((sc_dir / name).read_bytes()).hexdigest()
                lines.append(f"{h}  {name}")
            (sc_dir / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
            v = run([sys.executable, str(VERIFY), str(sc_dir)])
            if v.returncode != 1:
                fails.append(f"B6 expected exit 1 for contract hash mismatch, got {v.returncode}: {v.stderr.strip()}")
        else:
            # soft-when-absent: inject a fake contract with bad hash
            rep["score_contract"] = {
                "version": "0.1",
                "axes": [
                    {"name": "risk", "sense": "lower", "unit": "1", "formula_or_procedure_id": "test"},
                    {"name": "cost", "sense": "lower", "unit": "1", "formula_or_procedure_id": "test"},
                ],
            }
            rep["score_contract_hash"] = "0" * 64
            (sc_dir / "report.json").write_text(json.dumps(rep, indent=2) + "\n")
            lines = []
            for name in ("front.csv", "report.json"):
                h = hashlib.sha256((sc_dir / name).read_bytes()).hexdigest()
                lines.append(f"{h}  {name}")
            (sc_dir / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
            v = run([sys.executable, str(VERIFY), str(sc_dir)])
            if v.returncode != 1:
                fails.append(f"B6 expected exit 1 for injected bad contract hash, got {v.returncode}: {v.stderr.strip()}")

    if fails:
        for f in fails:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("B1–B6 acceptance GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
