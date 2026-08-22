#!/usr/bin/env python3
"""PGS-BUN / PGS-PRO / DOM-SC-001 — offline verifier for sealed pair-sieve front bundles.

Product: front.csv + report.json + MANIFEST.sha256
Exit 0 = pass. Exit 1 + one-line reason = fail.

V1: report.json parses; identity_ok true; identity_mode == fenwick_oracle
V2: MANIFEST.sha256 matches SHA256 of front.csv and report.json
V3: if chi_on: chi_pick present; chi_token is str containing r_chi=
V4: when chi_on, token lacking r_chi= FAILS (hash-only rejected)
V5: Score Contract — if score_contract / score_contract_hash absent → soft pass;
     if present → recompute hash via score_contract.verify_contract_hash or fail.

Verifier does not gate on promote_ready. No second kernel.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


def fail(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_front_ids(front_path: Path) -> set:
    ids = set()
    with front_path.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return ids
        fields = list(reader.fieldnames)
        id_key = None
        for cand in ("idx", "id", "index", "row"):
            if cand in fields:
                id_key = cand
                break
        for i, row in enumerate(reader):
            if id_key is not None:
                try:
                    ids.add(int(row[id_key]))
                except (TypeError, ValueError, KeyError):
                    pass
            else:
                ids.add(i)
    return ids


def verify_score_contract(report: dict) -> str | None:
    """Return error message or None if OK / soft-absent."""
    sc = report.get("score_contract")
    sch = report.get("score_contract_hash")
    if sc is None and sch is None:
        return None  # V5 soft-when-absent
    if sc is None or sch is None:
        return "score_contract and score_contract_hash must both be present or both absent"
    try:
        from score_contract import verify_contract_hash
    except ImportError:
        # fallback: recompute with same canonical rule if helper missing
        try:
            from score_contract import hash_contract
            if hash_contract(sc) != sch:
                return "score_contract_hash mismatch"
            return None
        except Exception as e:
            return f"score_contract verify unavailable: {e}"
    try:
        if not verify_contract_hash(sc, sch):
            return "score_contract_hash mismatch"
    except Exception as e:
        return f"score_contract verify error: {e}"
    return None


def verify(dir_path: Path, *, trust_hash: bool = True) -> int:
    if not dir_path.is_dir():
        return fail(f"bundle dir not found: {dir_path}")

    front = dir_path / "front.csv"
    report_path = dir_path / "report.json"
    manifest = dir_path / "MANIFEST.sha256"

    if not front.is_file():
        return fail("missing front.csv")
    if not report_path.is_file():
        return fail("missing report.json")
    if not manifest.is_file():
        return fail("missing MANIFEST.sha256")

    try:
        lines = [ln.strip() for ln in manifest.read_text().splitlines() if ln.strip()]
    except OSError as e:
        return fail(f"MANIFEST unreadable: {e}")

    expected = {}
    for ln in lines:
        parts = ln.split()
        if len(parts) < 2:
            return fail(f"MANIFEST malformed line: {ln!r}")
        hex_digest, name = parts[0], parts[-1]
        if name not in ("front.csv", "report.json"):
            return fail(f"MANIFEST unexpected entry: {name}")
        expected[name] = hex_digest

    if "front.csv" not in expected or "report.json" not in expected:
        return fail("MANIFEST must list front.csv and report.json")

    for name, want in expected.items():
        got = sha256_file(dir_path / name)
        if got != want:
            return fail(f"MANIFEST mismatch: {name}")

    try:
        report = json.loads(report_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return fail(f"report.json parse error: {e}")

    if not isinstance(report, dict):
        return fail("report.json is not an object")

    if report.get("identity_ok") is not True:
        return fail("identity_ok is not true")

    if report.get("identity_mode") != "fenwick_oracle":
        return fail(f"identity_mode is not fenwick_oracle: {report.get('identity_mode')!r}")

    sha = report.get("identity_sha256")
    if not isinstance(sha, str) or len(sha) < 16:
        return fail("identity_sha256 missing or short")

    chi_on = bool(report.get("chi_on"))
    if chi_on:
        token = report.get("chi_token")
        if token is None:
            return fail("chi_on but chi_token is null/missing")
        if not isinstance(token, str):
            return fail("chi_on but chi_token is not a string")
        if "r_chi=" not in token:
            return fail("chi_on but chi_token lacks r_chi= (hash-only rejected)")

        pick = report.get("chi_pick")
        if pick is None:
            return fail("chi_on but chi_pick missing")
        try:
            pick_i = int(pick)
        except (TypeError, ValueError):
            return fail(f"chi_pick not an int: {pick!r}")

        front_ids = load_front_ids(front)
        if front_ids and pick_i not in front_ids:
            return fail(f"chi_pick {pick_i} not in front ids")

    # V5 Score Contract
    sc_err = verify_score_contract(report)
    if sc_err:
        return fail(sc_err)

    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify sealed front bundle")
    ap.add_argument("dir", type=Path, help="bundle directory")
    ap.add_argument("--trust-hash", action="store_true", default=True)
    ap.add_argument("--no-trust-hash", action="store_true")
    args = ap.parse_args(argv)
    trust = not bool(args.no_trust_hash)
    return verify(args.dir, trust_hash=trust)


if __name__ == "__main__":
    raise SystemExit(main())
