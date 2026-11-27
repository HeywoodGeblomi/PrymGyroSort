#!/usr/bin/env python3
"""Receipt flag: stable except timestamp, book identity unchanged, tamper fails."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from receipt import brute_pair_check, sweep_weak_dominance  # noqa: E402
CLI = ROOT / "python" / "pair_sieve_cli.py"
VERIFY = ROOT / "python" / "verify_receipt.py"
BOOK = ROOT / "examples" / "book.csv"
BOOK_IDENTITY = "968b5b2b85e9c402664f05a44b240ae657b70a57d56ef59e392cd567b12e0121"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def _agree(name: str, X: np.ndarray, ranks: np.ndarray, fails: list[str], layers: np.ndarray | None = None) -> None:
    sweep = sweep_weak_dominance(X, ranks, layers)
    brute = brute_pair_check(X, ranks, layers)
    keys = ("locks", "rank_lock_violations", "layer_separation_violations", "tightness_failures")
    if tuple(sweep[k] for k in keys) != tuple(brute[k] for k in keys):
        fails.append(f"{name} sweep {sweep} brute {brute}")
    else:
        print(f"PASS agree {name}: { {k: sweep[k] for k in keys} }")


def check_sweep_against_brute(fails: list[str]) -> None:
    from prym_gyro import rank as native_rank

    import csv
    with BOOK.open(newline="") as f:
        book = np.array(
            [[float(r["risk"]), float(r["cost"])] for r in csv.DictReader(f)],
            dtype=np.float64,
        )
    book_ranks = native_rank(np.ascontiguousarray(book, dtype=np.float64))
    _agree("book", book, book_ranks, fails)

    from sklearn.datasets import fetch_openml
    ab = fetch_openml(name="abalone", version=1, as_frame=False, parser="liac-arff")
    names = list(ab.feature_names)
    cols = np.column_stack([
        -np.asarray(ab.data[:, names.index("Length")], dtype=np.float64),
        -np.asarray(ab.data[:, names.index("Whole_weight")], dtype=np.float64),
    ])
    ab_ranks = native_rank(np.ascontiguousarray(cols, dtype=np.float64))
    _agree("abalone", cols, ab_ranks, fails)

    for seed in range(12):
        rng = np.random.default_rng(seed)
        n = 60
        grid = np.column_stack([
            rng.integers(0, 6, size=n),
            rng.integers(0, 6, size=n),
        ]).astype(np.float64)
        # Repeat rows so identical coordinates are common.
        grid = np.vstack([grid, grid[:15]])
        got = native_rank(np.ascontiguousarray(grid, dtype=np.float64))
        _agree(f"ties_seed_{seed}", grid, got, fails)

    # (a) A dominates B in the same layer, while rank(A) < rank(B). Breaks layer separation only.
    same_layer = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]], dtype=np.float64)
    sweep = sweep_weak_dominance(
        same_layer,
        np.array([1, 2, 3], dtype=np.int32),
        np.array([1, 2, 2], dtype=np.int32),
    )
    if not (sweep["rank_lock_violations"] == 0 and sweep["layer_separation_violations"] >= 1 and sweep["tightness_failures"] == 0):
        fails.append(f"same-layer injection: {sweep}")
    else:
        print(f"PASS injected same layer: {sweep}")

    # (b) A dominates B and is ranked above B, but A sits in a worse layer. Breaks layer separation, not rank locks.
    worse_layer = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]], dtype=np.float64)
    sweep = sweep_weak_dominance(
        worse_layer,
        np.array([1, 2, 3], dtype=np.int32),
        np.array([1, 2, 1], dtype=np.int32),
    )
    if not (sweep["rank_lock_violations"] == 0 and sweep["layer_separation_violations"] >= 1):
        fails.append(f"worse-layer injection: {sweep}")
    else:
        print(f"PASS injected worse layer: {sweep}")

    # (c) Layers stay successive, but the rank order is swapped. Breaks rank locks only.
    swapped = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64)
    sweep = sweep_weak_dominance(
        swapped,
        np.array([2, 1], dtype=np.int32),
        np.array([1, 2], dtype=np.int32),
    )
    if not (sweep["rank_lock_violations"] >= 1 and sweep["layer_separation_violations"] == 0 and sweep["tightness_failures"] == 0):
        fails.append(f"rank-swap injection: {sweep}")
    else:
        print(f"PASS injected rank swap: {sweep}")

    # (d) Layer numbers jump from 1 to 3. Breaks tightness only.
    gap = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64)
    sweep = sweep_weak_dominance(
        gap,
        np.array([1, 2], dtype=np.int32),
        np.array([1, 3], dtype=np.int32),
    )
    if not (sweep["tightness_failures"] >= 1 and sweep["rank_lock_violations"] == 0 and sweep["layer_separation_violations"] == 0):
        fails.append(f"tightness injection: {sweep}")
    else:
        print(f"PASS injected tightness: {sweep}")


def check_housing_receipt(fails: list[str]) -> None:
    src = Path("/tmp/housing10k_c76.csv")
    if not src.is_file():
        fails.append("rebuilt 10k housing csv missing")
        return
    out = Path("/tmp/housing_receipt_sweep.json")
    t0 = time.perf_counter()
    result = run([
        sys.executable, str(CLI),
        "--csv", str(src),
        "--x-col", "median_income",
        "--y-col", "median_house_value",
        "--x-sense", "higher",
        "--y-sense", "higher",
        "--receipt", str(out),
    ])
    elapsed = time.perf_counter() - t0
    if result.returncode != 0:
        fails.append(f"housing receipt run failed: {result.stderr}")
        return
    receipt = json.loads(out.read_text())
    dom = receipt["dominance_verification"]
    if dom["method"] != "sweep_weak_dominance_v1" or dom["brute_force"]["method"] != "skipped":
        fails.append(f"housing dominance block {dom}")
    if dom["rank_lock_violations"] != 0 or dom["layer_separation_violations"] != 0 or dom["tightness_failures"] != 0:
        fails.append(f"housing sweep not clean: {dom}")
    checked = run([sys.executable, str(VERIFY), str(out), "--csv", str(src)])
    if checked.returncode != 0:
        fails.append(f"housing verifier failed: {checked.stderr}")
    else:
        from pair_sieve_cli import apply_senses, load_csv
        from prym_gyro import rank as native_rank
        matrix, _, _, _, _ = load_csv(src, "median_income", "median_house_value")
        matrix = apply_senses(matrix, "higher", "higher")
        got = native_rank(matrix)
        t_check = time.perf_counter()
        sweep_weak_dominance(matrix, got)
        check_s = time.perf_counter() - t_check
        print(
            f"PASS housing receipt verified rank_lock_violations={dom['rank_lock_violations']} "
            f"layer_separation_violations={dom['layer_separation_violations']} "
            f"tightness_failures={dom['tightness_failures']} locks={dom['locks']} "
            f"sweep_seconds={check_s:.4f} cli_seconds={elapsed:.3f}"
        )


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
            dom = ja["dominance_verification"]
            if dom["method"] != "sweep_weak_dominance_v1":
                fails.append("book dominance method")
            if dom["rank_lock_violations"] != 0 or dom["layer_separation_violations"] != 0 or dom["tightness_failures"] != 0:
                fails.append("book sweep counts")
            if not dom["vectors"]["same_vector"]:
                fails.append("book vectors")
            if dom["cross_check"] != "agree" or dom["brute_force"]["locks"] != 15890:
                fails.append(f"book cross-check {dom['cross_check']} {dom['brute_force']}")
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

    check_sweep_against_brute(fails)
    check_housing_receipt(fails)

    if fails:
        for item in fails:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    print("GREEN: receipt self-check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
