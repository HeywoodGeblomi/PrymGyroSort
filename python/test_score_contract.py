#!/usr/bin/env python3
"""DOM-AXX-001 Phase-A++.0 self-check: Score Contract hash + V5 soft/mismatch."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_contract import make_derived_contract, hash_contract, verify_contract_hash, canonical_dumps

def main() -> int:
    fails = []
    # 1. Determinism
    sc1, h1 = make_derived_contract("risk", "cost", "lower", "lower", "book.csv")
    sc2, h2 = make_derived_contract("risk", "cost", "lower", "lower", "book.csv")
    if h1 != h2 or sc1 != sc2:
        fails.append("derive not deterministic")
    if not verify_contract_hash(sc1, h1):
        fails.append("verify_contract_hash false on clean")
    if verify_contract_hash(sc1, "0" * 64):
        fails.append("verify_contract_hash true on bad hash")

    # 2. Canonical rule
    got = hash_contract(sc1)
    if got != h1:
        fails.append("hash_contract != make_derived hash")

    # 3. Sense / schema shape
    if sc1["schema_version"] != "0.1.0":
        fails.append("schema_version")
    if sc1["axes"][0]["sense"] != "lower" or sc1["axes"][1]["name"] != "cost":
        fails.append("axes content")
    if sc1.get("score_kind") != "observed" or sc1.get("derived") is not True:
        fails.append("score_kind / derived")

    # 4. Simulated report + V5 inline logic (no full CLI needed)
    report = {
        "identity_ok": True,
        "identity_mode": "fenwick_oracle",
        "identity_sha256": "abc",
        "score_contract": sc1,
        "score_contract_hash": h1,
    }
    # match
    if not verify_contract_hash(report["score_contract"], report["score_contract_hash"]):
        fails.append("V5 match failed")
    # mismatch
    report["score_contract_hash"] = "deadbeef" * 8
    if verify_contract_hash(report["score_contract"], report["score_contract_hash"]):
        fails.append("V5 should reject mismatch")

    # 5. California-shaped instance
    sc_ca, h_ca = make_derived_contract(
        "median_income", "median_house_value", "higher", "higher",
        "docs/stranger/filter_california_housing.py",
        units_x="10k USD", units_y="USD",
        procedure_id_x="docs/stranger/filter_california_housing.py:median_income",
        procedure_id_y="docs/stranger/filter_california_housing.py:median_house_value",
    )
    if not verify_contract_hash(sc_ca, h_ca):
        fails.append("california-shaped contract hash fail")
    if sc_ca["axes"][0].get("units") != "10k USD":
        fails.append("units not carried")

    if fails:
        print("FAIL:", fails)
        return 1
    print("GREEN: Score Contract helper + V5 logic self-check passed")
    print("example hash:", h1)
    print("california hash:", h_ca)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
