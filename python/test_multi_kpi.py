#!/usr/bin/env python3
"""k-score layers, cap-tie policies, and schema-v2 receipts.

--offline skips the rebuilt 10k housing file and abalone. Book, k=3, k=4,
cap policies, and the policy-record fault still run.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from multi_kpi import (  # noqa: E402
    DEFAULT_POLICY,
    DEFAULT_TIEBREAK,
    apply_cap,
    build_kpi_receipt,
    rank_layers,
    rank_layers_graph,
    rank_layers_relax,
)
from pair_sieve_cli import VERSION  # noqa: E402
from receipt import verify_receipt  # noqa: E402

BOOK = ROOT / "examples" / "book.csv"
BOOK_IDENTITY = "968b5b2b85e9c402664f05a44b240ae657b70a57d56ef59e392cd567b12e0121"
HOUSING_IDENTITY = "22cc811f06d78cf00792d4ccf941e96a09cd62b26170d9e58a93bcbc722fa67a"
HOUSING_SHA = "46ebf512a8b6f169ff3de79dd51fafd33b27d6152a9cfed6297d0324d8418216"
ABALONE_IDENTITY = "052efa5efb70e8c533aaa4ef09d8eb3fe7ae80ec027f28e38ce300d94831f7e7"
HOUSING_CANDIDATES = (Path("/tmp/housing10k_c76.csv"), Path("/tmp/housing_10k.csv"))


def sha256_ranks(ranks: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(ranks, dtype=np.int32).tobytes()).hexdigest()


def selected_rows(X: np.ndarray, mask: np.ndarray) -> list[tuple]:
    rows = []
    for i in np.flatnonzero(mask):
        rows.append(tuple(float(v) for v in X[int(i)]))
    rows.sort()
    return rows


def check_clean(fails: list[str], name: str, X: np.ndarray, ranks: np.ndarray) -> None:
    from receipt import brute_pair_check, vector_pair_check

    brute = brute_pair_check(X, ranks)
    vector = vector_pair_check(X, ranks)
    bad = (
        brute["rank_lock_violations"]
        or brute["layer_separation_violations"]
        or brute["tightness_failures"]
        or brute != vector
    )
    if bad:
        fails.append(f"{name} counts {brute} {vector}")
    else:
        print(
            f"PASS {name} locks={brute['locks']} "
            f"rank={brute['rank_lock_violations']} "
            f"layer={brute['layer_separation_violations']} "
            f"tight={brute['tightness_failures']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    fails: list[str] = []

    from multi_kpi import normalize_policy
    if DEFAULT_POLICY != "include_all_tied":
        fails.append(f"default {DEFAULT_POLICY}")
    elif normalize_policy(None, None) != ("include_all_tied", "none"):
        fails.append(f"normalize default {normalize_policy(None, None)}")
    elif normalize_policy("strict_cap", None) != ("strict_cap", DEFAULT_TIEBREAK):
        fails.append("strict_cap tiebreak default")
    else:
        print("PASS default policy include_all_tied; strict_cap still uses input_index")

    with BOOK.open(newline="") as f:
        book_rows = list(csv.DictReader(f))
    book = np.array([[float(r["risk"]), float(r["cost"])] for r in book_rows], dtype=np.float64)
    book_ranks = rank_layers(book)
    if sha256_ranks(book_ranks) != BOOK_IDENTITY:
        fails.append(f"book {sha256_ranks(book_ranks)}")
    else:
        print(f"PASS book fenwick identity {BOOK_IDENTITY}")
    graph = rank_layers_graph(book)
    relax = rank_layers_relax(book)
    if not (np.array_equal(book_ranks, graph) and np.array_equal(book_ranks, relax)):
        fails.append("book graph or relaxation diverged from Fenwick")
    else:
        print("PASS book graph and relaxation match Fenwick")
    check_clean(fails, "book", book, book_ranks)

    hand = np.array([
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [1.0, 1.0, 1.0],
        [0.0, 1.0, 1.0],
        [1.0, 0.0, 1.0],
    ], dtype=np.float64)
    hand_ranks = rank_layers(hand)
    if hand_ranks.tolist() != [1, 1, 3, 2, 2] or not np.array_equal(hand_ranks, rank_layers_relax(hand)):
        fails.append(f"k=3 hand {hand_ranks.tolist()}")
    else:
        print(f"PASS k=3 hand {hand_ranks.tolist()}")
    check_clean(fails, "k=3 hand", hand, hand_ranks)

    for k in (3, 4):
        for seed in range(8):
            rng = np.random.default_rng(1000 * k + seed)
            draw = rng.integers(0, 5, size=(36, k)).astype(np.float64)
            draw = np.vstack([draw, draw[:10]])
            got = rank_layers_graph(draw)
            oracle = rank_layers_relax(draw)
            if not np.array_equal(got, oracle):
                fails.append(f"k={k} seed={seed} graph != relax")
            else:
                check_clean(fails, f"k={k} seed={seed}", draw, got)

    swapped = hand_ranks.copy()
    swapped[0], swapped[3] = swapped[3], swapped[0]
    from receipt import brute_pair_check
    bad_counts = brute_pair_check(hand, swapped)
    if bad_counts["rank_lock_violations"] < 1 or bad_counts["layer_separation_violations"] < 1:
        fails.append(f"k=3 fault injection missed {bad_counts}")
    else:
        print(
            f"PASS k=3 injected swap rank={bad_counts['rank_lock_violations']} "
            f"layer={bad_counts['layer_separation_violations']}"
        )

    # Three incomparable rows. cap 1 splits layer 1.
    front = np.array([[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]], dtype=np.float64)
    front_ranks = rank_layers(front)
    if front_ranks.tolist() != [1, 1, 1]:
        fails.append(f"front ranks {front_ranks.tolist()}")
    policies = {
        "include_all_tied": ([1, 1, 1], 3, True),
        "exclude_tied": ([0, 0, 0], 0, True),
        "strict_cap": ([1, 0, 0], 1, False),
    }
    for name, (expect, count, invariant) in policies.items():
        key = "none" if name != "strict_cap" else None
        masks = []
        for _ in range(5):
            mask, record = apply_cap(front_ranks, 1, name, key)
            masks.append(mask.tobytes())
            if record["boundary_rows"] != 3 or record["selected_count"] != count:
                fails.append(f"{name} record {record}")
                break
            if record["permutation_invariant"] is not invariant:
                fails.append(f"{name} invariant flag {record}")
                break
        else:
            if len(set(masks)) != 1 or masks[0] != np.array(expect, dtype=np.int32).tobytes():
                fails.append(f"{name} mask {masks[0]!r}")
            else:
                print(f"PASS cap {name} repeated mask selected={count} boundary=3")

    exact = apply_cap(front_ranks, 3, "strict_cap")[1]
    overflow = apply_cap(front_ranks, 3, "include_all_tied", "none")[1]
    dropped = apply_cap(front_ranks, 3, "exclude_tied", "none")[1]
    if exact["boundary_rows"] != 0 or exact["selected_count"] != 3:
        fails.append(f"exact cap {exact}")
    elif len({exact["selection_sha256"], overflow["selection_sha256"], dropped["selection_sha256"]}) != 1:
        fails.append("exact boundary policies diverged")
    else:
        print("PASS exact layer boundary: all policies agree, boundary_rows=0")

    perm = front[[1, 0, 2]]
    perm_ranks = rank_layers(perm)
    base_all = selected_rows(front, apply_cap(front_ranks, 1, "include_all_tied", "none")[0])
    perm_all = selected_rows(perm, apply_cap(perm_ranks, 1, "include_all_tied", "none")[0])
    base_ex = selected_rows(front, apply_cap(front_ranks, 1, "exclude_tied", "none")[0])
    perm_ex = selected_rows(perm, apply_cap(perm_ranks, 1, "exclude_tied", "none")[0])
    base_st = selected_rows(front, apply_cap(front_ranks, 1, "strict_cap")[0])
    perm_st = selected_rows(perm, apply_cap(perm_ranks, 1, "strict_cap")[0])
    if base_all != perm_all or base_ex != perm_ex:
        fails.append("include/exclude changed under permutation")
    elif base_st == perm_st:
        fails.append("strict_cap input_index was permutation-invariant")
    else:
        print("PASS permutation: include/exclude invariant, strict_cap input_index is not")

    keys = np.array([5.0, 1.0, 9.0])
    keyed = apply_cap(front_ranks, 1, "strict_cap", "tie_key", keys)[0]
    if int(np.flatnonzero(keyed)[0]) != 1:
        fails.append(f"secondary key selected {keyed}")
    else:
        print("PASS strict_cap secondary key picks the lowest key")
    moved = np.array([1.0, 5.0, 9.0])
    moved_mask = apply_cap(perm_ranks, 1, "strict_cap", "tie_key", moved)[0]
    if selected_rows(front, keyed) != selected_rows(perm, moved_mask):
        fails.append("unique secondary key did not follow the row")
    else:
        print("PASS unique secondary key follows the row")
    tied_keys = np.array([4.0, 4.0, 4.0])
    tie_a = selected_rows(front, apply_cap(front_ranks, 1, "strict_cap", "tie_key", tied_keys)[0])
    tie_b = selected_rows(perm, apply_cap(perm_ranks, 1, "strict_cap", "tie_key", tied_keys)[0])
    if tie_a == tie_b:
        fails.append("equal secondary keys stayed invariant")
    else:
        print("PASS equal secondary keys fall back to input index")

    rng = np.random.default_rng(7)
    timed = rng.integers(0, 8, size=(1000, 4)).astype(np.float64)
    t0 = time.perf_counter()
    rank_layers_graph(timed)
    elapsed = time.perf_counter() - t0
    print(f"NOTE k=4 n=1000 dominance_graph_v1 one call {elapsed:.4f} s (one observation, not a speed claim)")

    with tempfile.TemporaryDirectory(prefix="pgs_kpi_") as td:
        td = Path(td)
        book_csv = BOOK
        out = td / "book_v2.json"
        receipt = build_kpi_receipt(
            out,
            adjusted=book,
            columns=[{"name": "risk", "sense": "lower"}, {"name": "cost", "sense": "lower"}],
            pair_sieve_version=VERSION,
            cap=4,
            input_path=book_csv,
        )
        if receipt["schema_version"] != "2" or receipt["output"]["identity_sha256"] != BOOK_IDENTITY:
            fails.append("book v2 identity")
        elif receipt["cap"]["policy"] != "include_all_tied" or receipt["cap"]["tiebreak_key"] != "none":
            fails.append(f"book v2 default cap {receipt['cap']}")
        elif receipt["cap"]["permutation_invariant"] is not True:
            fails.append("default receipt not marked order-independent")
        elif receipt["cap"]["selected_count"] != 7 or receipt["cap"]["boundary_rows"] != 7:
            fails.append(f"book default selection {receipt['cap']}")
        elif receipt["input"]["kpi_count"] != 2:
            fails.append("book kpi_count")
        else:
            problems = verify_receipt(receipt, csv_path=book_csv)
            dom = receipt["dominance_verification"]
            counts = (
                dom["rank_lock_violations"],
                dom["layer_separation_violations"],
                dom["tightness_failures"],
            )
            if problems or counts != (0, 0, 0):
                fails.append(f"book v2 verify {problems} {counts}")
            else:
                print(
                    f"PASS book v2 receipt boundary={receipt['cap']['boundary_rows']} "
                    f"selected={receipt['cap']['selected_count']} counts={counts}"
                )

        wrong = copy.deepcopy(receipt)
        wrong["cap"]["policy"] = "strict_cap"
        wrong["cap"]["tiebreak_key"] = "input_index"
        wrong["cap"]["permutation_invariant"] = False
        wrong_fails = verify_receipt(wrong, csv_path=book_csv)
        if not any("cap" in item for item in wrong_fails):
            fails.append(f"wrong policy was accepted {wrong_fails}")
        else:
            print(f"PASS verifier rejected wrong policy ({wrong_fails[0]})")

        cli_out = td / "cli_default.json"
        cli = subprocess.run(
            [
                sys.executable, str(ROOT / "python" / "pair_sieve_cli.py"),
                "--csv", str(BOOK),
                "--x-col", "risk",
                "--y-col", "cost",
                "--x-sense", "lower",
                "--y-sense", "lower",
                "--cap", "4",
                "--receipt", str(cli_out),
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        if cli.returncode != 0 or BOOK_IDENTITY not in cli.stdout:
            fails.append(f"cli default receipt {cli.returncode} {cli.stderr}")
        else:
            cli_receipt = json.loads(cli_out.read_text())
            if cli_receipt["cap"]["policy"] != "include_all_tied" or cli_receipt["schema_version"] != "2":
                fails.append(f"cli receipt policy {cli_receipt.get('cap')}")
            elif verify_receipt(cli_receipt, csv_path=BOOK):
                fails.append(f"cli receipt verify {verify_receipt(cli_receipt, csv_path=BOOK)}")
            else:
                print("PASS CLI default receipt records include_all_tied")

        # k=3 receipt on a small CSV, all three counts zero.
        k3_path = td / "k3.csv"
        with k3_path.open("w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["a", "b", "c", "tie_key"])
            for i, row in enumerate(hand):
                w.writerow([repr(float(row[0])), repr(float(row[1])), repr(float(row[2])), i])
        k3_receipt = build_kpi_receipt(
            td / "k3.json",
            adjusted=hand,
            columns=[
                {"name": "a", "sense": "lower"},
                {"name": "b", "sense": "lower"},
                {"name": "c", "sense": "lower"},
            ],
            pair_sieve_version=VERSION,
            cap=1,
            policy="strict_cap",
            tiebreak_key="tie_key",
            tiebreak_values=[0, 1, 2, 3, 4],
            input_path=k3_path,
        )
        k3_problems = verify_receipt(k3_receipt, csv_path=k3_path)
        k3_dom = k3_receipt["dominance_verification"]
        if k3_problems or k3_dom["method"] != "pair_weak_dominance_v1":
            fails.append(f"k3 receipt {k3_problems} {k3_dom.get('method')}")
        elif (k3_dom["rank_lock_violations"], k3_dom["layer_separation_violations"], k3_dom["tightness_failures"]) != (0, 0, 0):
            fails.append(f"k3 counts {k3_dom}")
        elif k3_receipt["output"]["rank_method"] != "dominance_graph_v1":
            fails.append("k3 rank method")
        else:
            print(
                f"PASS k=3 receipt selected={k3_receipt['cap']['selected_count']} "
                f"boundary={k3_receipt['cap']['boundary_rows']} "
                f"cross_check={k3_dom['cross_check']}"
            )

        if not args.offline:
            housing = None
            for candidate in HOUSING_CANDIDATES:
                if candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest() == HOUSING_SHA:
                    housing = candidate
                    break
            if housing is None:
                fails.append("rebuilt 10k housing csv missing")
            else:
                from pair_sieve_cli import apply_senses, load_csv
                matrix, _, _, _, _ = load_csv(housing, "median_income", "median_house_value")
                matrix = apply_senses(matrix, "higher", "higher")
                h_ranks = rank_layers(matrix)
                h_sha = sha256_ranks(h_ranks)
                front_n = int(np.sum(h_ranks == 1))
                layers_n = int(np.max(h_ranks))
                if h_sha != HOUSING_IDENTITY or front_n != 31 or layers_n != 602:
                    fails.append(f"housing {h_sha} front={front_n} layers={layers_n}")
                else:
                    print(f"PASS housing fenwick identity front={front_n} layers={layers_n}")
            try:
                from sklearn.datasets import fetch_openml
                ab = fetch_openml(name="abalone", version=1, as_frame=False, parser="liac-arff")
                names = list(ab.feature_names)
                cols = np.column_stack([
                    -np.asarray(ab.data[:, names.index("Length")], dtype=np.float64),
                    -np.asarray(ab.data[:, names.index("Whole_weight")], dtype=np.float64),
                ])
                a_sha = sha256_ranks(rank_layers(cols))
                if a_sha != ABALONE_IDENTITY:
                    fails.append(f"abalone {a_sha}")
                else:
                    print(f"PASS abalone fenwick identity {a_sha}")
            except Exception as e:
                fails.append(f"abalone unavailable: {e}")

    if fails:
        for item in fails:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    print("GREEN: multi-KPI and cap-tie")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
