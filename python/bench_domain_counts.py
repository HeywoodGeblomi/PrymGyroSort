#!/usr/bin/env python3
"""Lock counts and cap-boundary counts on documented public sets.

Prints counts and wall times only. No prices, no cost model, no efficacy claim.
Policies are named on every cap row; the result does not depend on which
policy is the default.

k = 2 uses exact_rank_2d_fenwick. k > 2 uses dominance_graph_v1, O(k n^2)
time and O(n + E) memory. Times below are one measured call each.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "python"))

from multi_kpi import apply_cap, rank_layers  # noqa: E402
from pair_sieve_cli import apply_senses, load_csv  # noqa: E402
from receipt import dominance_check  # noqa: E402

BOOK = ROOT / "examples" / "book.csv"
HOUSING_CANDIDATES = (Path("/tmp/housing10k_c76.csv"), Path("/tmp/housing_10k.csv"))
HOUSING_SHA = "46ebf512a8b6f169ff3de79dd51fafd33b27d6152a9cfed6297d0324d8418216"
POLICIES = ("include_all_tied", "exclude_tied", "strict_cap")


def sha256_ranks(ranks: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(ranks, dtype=np.int32).tobytes()).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timed(fn):
    t0 = time.perf_counter()
    value = fn()
    return value, time.perf_counter() - t0


def cap_rows(ranks: np.ndarray, caps: list[int]) -> list[dict]:
    rows = []
    for cap in caps:
        for policy in POLICIES:
            key = None if policy == "strict_cap" else "none"
            _mask, record = apply_cap(ranks, cap, policy, key)
            rows.append({
                "cap": cap,
                "policy": record["policy"],
                "tiebreak_key": record["tiebreak_key"],
                "boundary_rows": record["boundary_rows"],
                "selected_count": record["selected_count"],
            })
    return rows


def summarize(name: str, source: str, matrix: np.ndarray, columns: list[dict], caps: list[int], file_sha: str | None) -> dict:
    data = np.ascontiguousarray(matrix, dtype=np.float64)
    ranks, rank_s = timed(lambda: rank_layers(data))
    dom, check_s = timed(lambda: dominance_check(data, ranks))
    return {
        "dataset": name,
        "source": source,
        "file_sha256": file_sha,
        "columns": columns,
        "n": int(data.shape[0]),
        "k": int(data.shape[1]),
        "layer_count": int(np.max(ranks)) if ranks.size else 0,
        "front_size": int(np.sum(ranks == 1)),
        "locks": dom["locks"],
        "rank_lock_violations": dom["rank_lock_violations"],
        "layer_separation_violations": dom["layer_separation_violations"],
        "tightness_failures": dom["tightness_failures"],
        "dominance_method": dom["method"],
        "cross_check": dom["cross_check"],
        "identity_sha256": sha256_ranks(ranks),
        "rank_seconds": rank_s,
        "check_seconds": check_s,
        "caps": cap_rows(ranks, caps),
    }


def load_book():
    with BOOK.open(newline="") as f:
        rows = list(csv.DictReader(f))
    matrix = np.array([[float(r["risk"]), float(r["cost"])] for r in rows], dtype=np.float64)
    return matrix, [
        {"name": "risk", "sense": "lower"},
        {"name": "cost", "sense": "lower"},
    ]


def find_housing() -> Path:
    for path in HOUSING_CANDIDATES:
        if path.is_file() and sha256_file(path) == HOUSING_SHA:
            return path
    raise SystemExit("rebuilt 10k housing csv not found (sha256 46ebf512...)")


def load_abalone():
    from sklearn.datasets import fetch_openml
    bunch = fetch_openml(name="abalone", version=1, as_frame=False, parser="liac-arff")
    names = list(bunch.feature_names)
    length = np.asarray(bunch.data[:, names.index("Length")], dtype=np.float64)
    weight = np.asarray(bunch.data[:, names.index("Whole_weight")], dtype=np.float64)
    # Both higher-is-better, so the kernel sees the negated values.
    matrix = np.column_stack([-length, -weight])
    columns = [
        {"name": "Length", "sense": "higher"},
        {"name": "Whole_weight", "sense": "higher"},
    ]
    return matrix, columns, str(bunch.details.get("id", ""))


def load_diabetes():
    """Eight scores from sklearn load_diabetes.

    Columns, in order: bmi, bp, s1, s2, s3, s4, s5, s6.
    s3 is higher-is-better. The other seven are lower-is-better.
    age, sex, and target are not scores. This is the eight-column set named
    in docs/stranger/DISAGREEMENTS_v2.md.
    """
    from sklearn.datasets import load_diabetes
    bunch = load_diabetes()
    names = list(bunch.feature_names)
    keep = ["bmi", "bp", "s1", "s2", "s3", "s4", "s5", "s6"]
    columns = []
    parts = []
    for name in keep:
        values = np.asarray(bunch.data[:, names.index(name)], dtype=np.float64)
        sense = "higher" if name == "s3" else "lower"
        parts.append(-values if sense == "higher" else values)
        columns.append({"name": name, "sense": sense})
    return np.column_stack(parts), columns


def cpu_name() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if not cpuinfo.is_file():
        return platform.processor() or "unknown"
    for line in cpuinfo.read_text(errors="replace").splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    book, book_cols = load_book()
    housing_path = find_housing()
    housing, _, _, _, _ = load_csv(housing_path, "median_income", "median_house_value")
    housing = apply_senses(housing, "higher", "higher")
    abalone, ab_cols, ab_id = load_abalone()
    diabetes, dia_cols = load_diabetes()

    rows = [
        summarize(
            "book",
            "examples/book.csv in this repo; risk and cost, both lower-is-better",
            book,
            book_cols,
            [1, 7, 10],
            sha256_file(BOOK),
        ),
        summarize(
            "housing_10k",
            "public California housing rebuild in docs/stranger/SOURCE.md: "
            "median_income and median_house_value, both higher-is-better, "
            "first 10000 finite rows, caps kept. Not the 40-row sample.",
            housing,
            [
                {"name": "median_income", "sense": "higher"},
                {"name": "median_house_value", "sense": "higher"},
            ],
            [1, 31, 100],
            sha256_file(housing_path),
        ),
        summarize(
            "abalone",
            f"OpenML abalone version 1 (details id {ab_id}); Length and Whole_weight, both higher-is-better",
            abalone,
            ab_cols,
            [1, 5, 20],
            None,
        ),
        summarize(
            "diabetes",
            "sklearn load_diabetes; bmi, bp, s1, s2, s3, s4, s5, s6; s3 higher-is-better, the other seven lower-is-better; age, sex, and target unused",
            diabetes,
            dia_cols,
            [1, 75, 100],
            None,
        ),
    ]
    payload = {
        "machine": {
            "platform": platform.platform(),
            "cpu": cpu_name(),
            "python": platform.python_version(),
        },
        "note": "Times are one perf_counter call each. k>2 is the dominance graph. No extrapolated times.",
        "datasets": rows,
    }
    print(f"cpu: {payload['machine']['cpu']}")
    print(f"platform: {payload['machine']['platform']}")
    print()
    print("| dataset | n | k | layers | front | locks | rank viol | layer viol | tight | rank s | check s | cross_check | identity |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for row in rows:
        print(
            f"| {row['dataset']} | {row['n']} | {row['k']} | {row['layer_count']} | {row['front_size']} | "
            f"{row['locks']} | {row['rank_lock_violations']} | {row['layer_separation_violations']} | "
            f"{row['tightness_failures']} | {row['rank_seconds']:.4f} | {row['check_seconds']:.4f} | "
            f"{row['cross_check']} | {row['identity_sha256']} |"
        )
        print(f"source {row['dataset']}: {row['source']}")
        if row["file_sha256"]:
            print(f"file sha256 {row['dataset']}: {row['file_sha256']}")
        print("| cap | policy | tiebreak | boundary_rows | selected_count |")
        print("|---:|---|---|---:|---:|")
        for cap in row["caps"]:
            print(
                f"| {cap['cap']} | {cap['policy']} | {cap['tiebreak_key']} | "
                f"{cap['boundary_rows']} | {cap['selected_count']} |"
            )
        print()
    if args.json:
        args.json.write_text(json.dumps(payload, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
