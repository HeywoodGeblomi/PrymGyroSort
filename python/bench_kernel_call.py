#!/usr/bin/env python3
"""Time exact_rank_2d_fenwick in memory, and the Python two-array call.

Kernel-only time is the C++ call with the (N, 2) matrix already resident.
Python-call time is prym_gyro.exact_rank_2d on two resident float64 arrays.
Neither measurement reads the CSV inside the timed loop.

Protocol: one untimed warmup, then 11 timed calls. The median is the middle
of those 11 sorted times. Spread is the minimum, maximum, and sample standard
deviation of the same 11.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "python"))

from pair_sieve_cli import apply_senses, load_csv  # noqa: E402
from prym_gyro import exact_rank_2d, kernel_times_ms  # noqa: E402

BOOK = ROOT / "examples" / "book.csv"
HOUSING_CANDIDATES = (
    Path("/tmp/housing10k_c76.csv"),
    Path("/tmp/housing_10k.csv"),
)
HOUSING_SHA = "46ebf512a8b6f169ff3de79dd51fafd33b27d6152a9cfed6297d0324d8418216"
WARMUP = 1
REPS = 11


def sha256_ranks(ranks: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(ranks, dtype=np.int32).tobytes()).hexdigest()


def summarize(times: list[float]) -> dict:
    sample = list(times)
    ordered = sorted(sample)
    return {
        "n": len(sample),
        "median_ms": ordered[len(ordered) // 2],
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "stdev_ms": statistics.stdev(sample) if len(sample) > 1 else 0.0,
        "times_ms": sample,
    }


def machine_notes() -> dict:
    cpu = "unknown"
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(errors="replace").splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    compiler = ""
    try:
        compiler = subprocess.check_output(["g++", "--version"], text=True).splitlines()[0]
    except (OSError, subprocess.CalledProcessError):
        compiler = "g++ not on PATH"
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu": cpu,
        "cpu_count": __import__("os").cpu_count(),
        "compiler": compiler,
        "compile_flags": "setuptools -O2 -fPIC, then -O3 -std=c++17 -fvisibility=hidden (last -O flag is -O3)",
        "kernel_clock": "std::chrono::steady_clock around exact_rank_2d_fenwick only",
        "python_clock": "time.perf_counter around exact_rank_2d(xs, ys)",
        "protocol": f"{WARMUP} untimed warmup, then {REPS} timed calls; median is the middle sorted value",
    }


def load_book():
    with BOOK.open(newline="") as f:
        rows = list(csv.DictReader(f))
    xs = np.asarray([float(r["risk"]) for r in rows], dtype=np.float64)
    ys = np.asarray([float(r["cost"]) for r in rows], dtype=np.float64)
    return xs, ys


def find_housing() -> Path:
    for path in HOUSING_CANDIDATES:
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == HOUSING_SHA:
            return path
    raise SystemExit("rebuilt 10k housing csv not found")


def python_times(xs: np.ndarray, ys: np.ndarray) -> tuple[list[float], np.ndarray]:
    exact_rank_2d(xs, ys)
    times = []
    last = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        last = exact_rank_2d(xs, ys)
        times.append((time.perf_counter() - t0) * 1e3)
    return times, last


def measure(name: str, xs: np.ndarray, ys: np.ndarray) -> dict:
    xs = np.ascontiguousarray(xs, dtype=np.float64).reshape(-1)
    ys = np.ascontiguousarray(ys, dtype=np.float64).reshape(-1)
    matrix = np.ascontiguousarray(np.column_stack([xs, ys]), dtype=np.float64)
    kernel = kernel_times_ms(matrix, WARMUP + REPS)
    py_times, py_ranks = python_times(xs, ys)
    kernel_sample = kernel["times_ms"][WARMUP:]
    identity = sha256_ranks(py_ranks)
    if sha256_ranks(kernel["ranks"]) != identity:
        raise SystemExit(f"{name}: kernel timer ranks differ from Python call")
    return {
        "name": name,
        "n": int(xs.shape[0]),
        "identity_sha256": identity,
        "front_size": int(np.sum(py_ranks == 1)),
        "layer_count": int(np.max(py_ranks)) if py_ranks.size else 0,
        "kernel_only": summarize(kernel_sample),
        "python_call": summarize(py_times),
    }


def fmt(row: dict, which: str) -> str:
    s = row[which]
    return (
        f"{s['median_ms']:.5f} | {s['min_ms']:.5f} | {s['max_ms']:.5f} | {s['stdev_ms']:.5f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    book_x, book_y = load_book()
    housing = find_housing()
    matrix, _, _, _, _ = load_csv(housing, "median_income", "median_house_value")
    matrix = apply_senses(matrix, "higher", "higher")
    rows = [
        measure("book", book_x, book_y),
        measure("housing_10k", matrix[:, 0], matrix[:, 1]),
    ]
    notes = machine_notes()
    payload = {"machine": notes, "datasets": rows}
    print(f"cpu: {notes['cpu']}")
    print(f"platform: {notes['platform']} cpus={notes['cpu_count']}")
    print(f"compiler: {notes['compiler']}")
    print(f"flags: {notes['compile_flags']}")
    print(f"protocol: {notes['protocol']}")
    print()
    print("| dataset | n | path | median ms | min ms | max ms | stdev ms |")
    print("|---|---:|---|---:|---:|---:|---:|")
    for row in rows:
        print(f"| {row['name']} | {row['n']} | kernel-only | {fmt(row, 'kernel_only')} |")
        print(f"| {row['name']} | {row['n']} | python-call | {fmt(row, 'python_call')} |")
        print(f"identity {row['name']}: {row['identity_sha256']} front={row['front_size']} layers={row['layer_count']}")
    if args.json:
        args.json.write_text(json.dumps(payload, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
