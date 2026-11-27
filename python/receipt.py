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


SWEEP_METHOD = "sweep_weak_dominance_v1"


class _Bit2D:
    """Sparse 2D Fenwick tree. Both axes are 1-based inclusive prefix sums."""

    def __init__(self, nx: int, ny: int):
        self.nx = nx
        self.ny = ny
        self.rows: dict[int, dict[int, int]] = {}

    def add(self, x: int, y: int, delta: int) -> None:
        while x <= self.nx:
            row = self.rows.get(x)
            if row is None:
                row = {}
                self.rows[x] = row
            yy = y
            while yy <= self.ny:
                row[yy] = row.get(yy, 0) + delta
                yy += yy & -yy
            x += x & -x

    def prefix(self, x: int, y: int) -> int:
        total = 0
        while x > 0:
            row = self.rows.get(x)
            if row:
                yy = y
                while yy > 0:
                    total += row.get(yy, 0)
                    yy -= yy & -yy
            x -= x & -x
        return total


def brute_pair_check(X: np.ndarray, ranks: np.ndarray) -> tuple[int, int, int]:
    """Ordered dominating pairs, pair violations, and rows that skip a layer."""
    n = int(X.shape[0])
    locks = 0
    violations = 0
    tightness_failures = 0
    rank_list = [int(v) for v in ranks]
    for i in range(n):
        ri = rank_list[i]
        has_prev = False
        xi0, xi1 = float(X[i, 0]), float(X[i, 1])
        for j in range(n):
            if i == j:
                continue
            xj0, xj1 = float(X[j, 0]), float(X[j, 1])
            if (xj0 <= xi0 and xj1 <= xi1) and (xj0 < xi0 or xj1 < xi1):
                locks += 1
                rj = rank_list[j]
                if rj >= ri:
                    violations += 1
                if ri > 1 and rj == ri - 1:
                    has_prev = True
        if ri > 1 and not has_prev:
            tightness_failures += 1
    return locks, violations, tightness_failures


def sweep_weak_dominance(X: np.ndarray, ranks: np.ndarray) -> dict:
    """Count locks, rank violations, and tightness gaps in O(n log n) memory.

    Points are swept in (x, y, index) order. A Fenwick query sees every
    already-inserted point with y' <= y. Inserts are flushed only when the
    (x, y) pair changes, so identical rows do not dominate each other, a
    same-x better y does, and a smaller x with the same y does.
    """
    n = int(X.shape[0])
    empty = {"locks": 0, "violations": 0, "tightness_failures": 0}
    if n == 0:
        return empty
    xs = np.asarray(X[:, 0], dtype=np.float64)
    ys = np.asarray(X[:, 1], dtype=np.float64)
    rank_list = [int(v) for v in np.asarray(ranks).reshape(-1)]
    if len(rank_list) != n:
        raise ValueError("ranks length does not match rows")
    y_values = np.unique(ys)
    y_index = {float(v): i + 1 for i, v in enumerate(y_values.tolist())}
    rank_values = sorted(set(rank_list))
    rank_index = {v: i + 1 for i, v in enumerate(rank_values)}
    bit = _Bit2D(len(y_values), len(rank_values))
    order = np.lexsort((np.arange(n), ys, xs))
    locks = 0
    violations = 0
    tightness_failures = 0

    def query(y_pos: int, rank_pos: int) -> int:
        if rank_pos <= 0:
            return 0
        return bit.prefix(y_pos, rank_pos)

    i = 0
    while i < n:
        j = i + 1
        xi = float(xs[order[i]])
        yi = float(ys[order[i]])
        while j < n and float(xs[order[j]]) == xi and float(ys[order[j]]) == yi:
            j += 1
        y_pos = y_index[yi]
        for k in range(i, j):
            idx = int(order[k])
            ri = rank_list[idx]
            rpos = rank_index[ri]
            dominators = query(y_pos, len(rank_values))
            bad = dominators - query(y_pos, rpos - 1)
            prev = query(y_pos, rank_index[ri - 1]) - query(y_pos, rank_index[ri - 1] - 1) if (ri - 1) in rank_index else 0
            locks += dominators
            violations += bad
            if ri > 1 and prev == 0:
                tightness_failures += 1
        for k in range(i, j):
            idx = int(order[k])
            bit.add(y_index[yi], rank_index[rank_list[idx]], 1)
        i = j
    return {
        "locks": locks,
        "violations": violations,
        "tightness_failures": tightness_failures,
    }


def dominance_check(X: np.ndarray, ranks: np.ndarray) -> dict:
    sweep = sweep_weak_dominance(X, ranks)
    n = int(X.shape[0])
    if n > BRUTE_PAIR_LIMIT:
        brute = {
            "method": "skipped",
            "reason": f"row_count {n} exceeds brute-force pair-check limit {BRUTE_PAIR_LIMIT}",
            "locks": None,
            "violations": None,
            "tightness_failures": None,
            "limit_n": BRUTE_PAIR_LIMIT,
        }
        cross = "not_run"
    else:
        locks, violations, tight = brute_pair_check(X, ranks)
        brute = {
            "method": "brute_force_weak_dominance",
            "reason": None,
            "locks": locks,
            "violations": violations,
            "tightness_failures": tight,
            "limit_n": BRUTE_PAIR_LIMIT,
        }
        cross = (
            "agree"
            if (
                locks == sweep["locks"]
                and violations == sweep["violations"]
                and tight == sweep["tightness_failures"]
            )
            else "disagree"
        )
    return {
        "method": SWEEP_METHOD,
        "locks": sweep["locks"],
        "violations": sweep["violations"],
        "tightness_failures": sweep["tightness_failures"],
        "brute_force": brute,
        "cross_check": cross,
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
    if dom.get("method") != SWEEP_METHOD:
        fails.append("dominance method")
    if dom.get("locks") is None or dom.get("violations") is None or dom.get("tightness_failures") is None:
        fails.append("sweep counts missing")
    brute = dom.get("brute_force") or {}
    if brute.get("method") == "brute_force_weak_dominance":
        if brute.get("locks") is None or brute.get("violations") is None:
            fails.append("brute counts missing")
        if dom.get("cross_check") != "agree":
            fails.append("sweep and brute disagree")
    elif brute.get("method") == "skipped":
        if not brute.get("reason"):
            fails.append("brute skip reason missing")
        if dom.get("cross_check") != "not_run":
            fails.append("cross_check")
    else:
        fails.append("brute method")
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
    for key in ("method", "locks", "violations", "tightness_failures", "cross_check"):
        if dom.get(key) != recorded.get(key):
            fails.append(f"dominance {key} mismatch on rerun")
            break
    bgot = dom.get("brute_force") or {}
    brec = recorded.get("brute_force") or {}
    for key in ("method", "locks", "violations", "tightness_failures"):
        if bgot.get(key) != brec.get(key):
            fails.append(f"brute {key} mismatch on rerun")
            break
    return fails
