"""DOM-AXX-001 / Phase-A++.0 — Score Contract helper.

Single source of truth for canonical serialization + hash.
Used by pair_sieve_cli (sealer) and verify_bundle (verifier).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Tuple


SCHEMA_VERSION = "0.1.0"
HASH_ALG = "sha256"


def canonical_dumps(obj: Dict[str, Any]) -> str:
    """Deterministic JSON for hashing. Locked rule from Score Contract v0.1."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_contract(contract: Dict[str, Any]) -> str:
    """sha256 hex of the canonical form."""
    return hashlib.sha256(canonical_dumps(contract).encode("utf-8")).hexdigest()


def make_derived_contract(
    x_name: str,
    y_name: str,
    x_sense: str,
    y_sense: str,
    source: str,
    *,
    score_kind: str = "observed",
    units_x: Optional[str] = None,
    units_y: Optional[str] = None,
    procedure_id_x: Optional[str] = None,
    procedure_id_y: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Build a minimal Score Contract from CLI column names + senses.
    Returns (contract_dict, contract_hash).
    """
    ax0: Dict[str, Any] = {
        "name": str(x_name),
        "sense": x_sense,
        "formula_or_procedure_id": procedure_id_x or f"cli:{source}",
    }
    if units_x:
        ax0["units"] = units_x
    ax1: Dict[str, Any] = {
        "name": str(y_name),
        "sense": y_sense,
        "formula_or_procedure_id": procedure_id_y or f"cli:{source}",
    }
    if units_y:
        ax1["units"] = units_y

    contract: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "axes": [ax0, ax1],
        "score_kind": score_kind,
        "hash_alg": HASH_ALG,
        "derived": True,
    }
    return contract, hash_contract(contract)


def verify_contract_hash(contract: Dict[str, Any], claimed_hash: str) -> bool:
    """Return True iff claimed_hash matches the canonical hash of contract."""
    if not isinstance(contract, dict) or not isinstance(claimed_hash, str):
        return False
    return hash_contract(contract) == claimed_hash
