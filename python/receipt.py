#!/usr/bin/env python3
"""Per-run JSON receipt. Off unless the CLI is given --receipt.

Records hashes and a dominance pair check. It does not change rank bytes.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KERNEL_REL = "cpp/include/gyro_rank.hpp"
SCHEMA_VERSION = "1"
BRUTE_PAIR_LIMIT = 2000

from verify_bundle import sha256_file  # noqa: E402


def ranks_sha256(ranks) -> str:
    arr = np.ascontiguousarray(ranks, dtype=np.int32)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def git_commit(repo: Path = ROOT) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    sha = out.stdout.strip()
    return sha or None


def module_path() -> Path | None:
    try:
        import prym_gyro_native as native
    except ImportError:
        return None
    file = getattr(native, "__file__", None)
    return Path(file) if file else None


def weakly_dominates(a, b) -> bool:
    return (a[0] <= b[0] and a[1] <= b[1]) and (a[0] < b[0] or a[1] < b[1])


def dominance_check(X: np.ndarray, ranks: np.ndarray) -> dict:
    n = int(X.shape[0])
    if n > BRUTE_PAIR_LIMIT:
        return {
            "method": "skipped",
            "reason": f"row_count {n} exceeds brute-force pair-check limit {BRUTE_PAIR_LIMIT}",
            "locks": None,
            "violations": None,
            "limit_n": BRUTE_PAIR_LIMIT,
        }
    locks = 0
    violations = 0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if weakly_dominates(X[j], X[i]):
                locks += 1
                if not (int(ranks[j]) < int(ranks[i])):
                    violations += 1
    return {
        "method": "brute_force_weak_dominance",
        "reason": None,
        "locks": locks,
        "violations": violations,
        "limit_n": BRUTE_PAIR_LIMIT,
    }


def _tool_versions(pair_sieve_version: str) -> dict:
    numpy_version = None
    try:
        numpy_version = np.__version__
    except Exception:
        numpy_version = None
    return {
        "python": platform.python_version(),
        "numpy": numpy_version,
        "pair_sieve": pair_sieve_version,
        "platform": platform.platform(),
    }


def build_receipt(
    *,
    input_path: Path | None,
    row_count: int,
    columns: list[dict],
    ranks: np.ndarray,
    adjusted: np.ndarray,
    pair_sieve_version: str,
    repo: Path = ROOT,
) -> dict:
    kernel = repo / KERNEL_REL
    mod = module_path()
    identity = ranks_sha256(ranks)
    front_size = int(np.sum(np.asarray(ranks) == 1))
    layer_count = int(np.max(ranks)) if len(ranks) else 0
    if input_path is not None and input_path.is_file():
        try:
            rel = input_path.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            rel = str(input_path)
        file_sha = sha256_file(input_path)
    else:
        rel = None
        file_sha = None
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input": {
            "path": rel,
            "sha256": file_sha,
            "row_count": int(row_count),
            "columns": columns,
        },
        "kernel": {
            "source_path": KERNEL_REL,
            "source_sha256": sha256_file(kernel) if kernel.is_file() else None,
            "module_path": str(mod) if mod else None,
            "module_sha256": sha256_file(mod) if mod and mod.is_file() else None,
        },
        "git_commit": git_commit(repo),
        "output": {
            "identity_sha256": identity,
            "front_size": front_size,
            "layer_count": layer_count,
        },
        "dominance_verification": dominance_check(adjusted, ranks),
        "tools": _tool_versions(pair_sieve_version),
    }


def write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def comparable(receipt: dict) -> dict:
    out = json.loads(json.dumps(receipt))
    out.pop("timestamp_utc", None)
    return out


def verify_receipt(
    receipt: dict,
    *,
    csv_path: Path | None = None,
    repo: Path = ROOT,
    rerun: bool = True,
) -> list[str]:
    """Return a list of failures. Empty means the receipt matches the inputs."""
    fails: list[str] = []
    if receipt.get("schema_version") != SCHEMA_VERSION:
        fails.append("schema_version")
    inp = receipt.get("input") or {}
    if csv_path is not None:
        if not csv_path.is_file():
            fails.append(f"csv missing: {csv_path}")
        else:
            got = sha256_file(csv_path)
            if got != inp.get("sha256"):
                fails.append(f"input sha256 {got} != {inp.get('sha256')}")
            with csv_path.open(newline="") as f:
                import csv as _csv
                n = sum(1 for _ in _csv.DictReader(f))
            if n != inp.get("row_count"):
                fails.append(f"row_count {n} != {inp.get('row_count')}")
    kernel = repo / (receipt.get("kernel") or {}).get("source_path", KERNEL_REL)
    if kernel.is_file():
        got = sha256_file(kernel)
        if got != (receipt.get("kernel") or {}).get("source_sha256"):
            fails.append("kernel source sha256")
    dom = receipt.get("dominance_verification") or {}
    if dom.get("method") == "brute_force_weak_dominance":
        if dom.get("locks") is None or dom.get("violations") is None:
            fails.append("dominance counts missing")
    elif dom.get("method") == "skipped":
        if not dom.get("reason"):
            fails.append("skip reason missing")
    else:
        fails.append("dominance method")
    out = receipt.get("output") or {}
    if not out.get("identity_sha256") or out.get("front_size") is None or out.get("layer_count") is None:
        fails.append("output fields")
    if rerun and csv_path is not None and csv_path.is_file() and not fails:
        fails.extend(_rerun_checks(receipt, csv_path))
    return fails


def _rerun_checks(receipt: dict, csv_path: Path) -> list[str]:
    fails = []
    try:
        from pair_sieve_cli import apply_senses, load_csv
        from prym_gyro import rank as native_rank
    except Exception as e:
        return [f"rerun unavailable: {e}"]
    cols = receipt["input"]["columns"]
    if len(cols) != 2:
        return ["columns"]
    X, _, _, _, _ = load_csv(csv_path, cols[0]["name"], cols[1]["name"])
    X = apply_senses(X, cols[0]["sense"], cols[1]["sense"])
    ranks = native_rank(X)
    if ranks_sha256(ranks) != receipt["output"]["identity_sha256"]:
        fails.append("identity mismatch on rerun")
    front = int(np.sum(ranks == 1))
    layers = int(np.max(ranks)) if len(ranks) else 0
    if front != receipt["output"]["front_size"]:
        fails.append("front_size mismatch on rerun")
    if layers != receipt["output"]["layer_count"]:
        fails.append("layer_count mismatch on rerun")
    dom = dominance_check(X, ranks)
    recorded = receipt["dominance_verification"]
    if dom["method"] != recorded.get("method"):
        fails.append("dominance method mismatch on rerun")
    elif dom["method"] == "brute_force_weak_dominance":
        if dom["locks"] != recorded.get("locks") or dom["violations"] != recorded.get("violations"):
            fails.append("dominance counts mismatch on rerun")
    return fails
