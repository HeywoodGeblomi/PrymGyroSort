#!/usr/bin/env python3
"""Two-array exact_rank_2d binding vs the CLI rank path.

Offline (default in CI): book, Python lists, tie-heavy random draws, and a
book receipt. Full mode also checks the rebuilt 10k housing file and abalone.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from pair_sieve_cli import VERSION, apply_senses, load_csv  # noqa: E402
from prym_gyro import exact_rank_2d, rank, rank_fenwick_ref, write_score_receipt  # noqa: E402
from receipt import verify_receipt  # noqa: E402

BOOK = ROOT / "examples" / "book.csv"
BOOK_IDENTITY = "968b5b2b85e9c402664f05a44b240ae657b70a57d56ef59e392cd567b12e0121"
HOUSING_IDENTITY = "22cc811f06d78cf00792d4ccf941e96a09cd62b26170d9e58a93bcbc722fa67a"
HOUSING_SHA = "46ebf512a8b6f169ff3de79dd51fafd33b27d6152a9cfed6297d0324d8418216"
ABALONE_IDENTITY = "052efa5efb70e8c533aaa4ef09d8eb3fe7ae80ec027f28e38ce300d94831f7e7"
HOUSING_CANDIDATES = (
    Path("/tmp/housing10k_c76.csv"),
    Path("/tmp/housing_10k.csv"),
)


def sha256_ranks(ranks: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(ranks, dtype=np.int32).tobytes()).hexdigest()


def matches_cli(X: np.ndarray, ranks: np.ndarray) -> bool:
    via_rank = np.ascontiguousarray(rank(X), dtype=np.int32)
    via_ref = np.ascontiguousarray(rank_fenwick_ref(X), dtype=np.int32)
    got = np.ascontiguousarray(ranks, dtype=np.int32)
    return got.tobytes() == via_rank.tobytes() == via_ref.tobytes()


def check_zero_receipt(fails: list[str], name: str, receipt: dict, csv_path: Path) -> None:
    problems = verify_receipt(receipt, csv_path=csv_path)
    dom = receipt["dominance_verification"]
    counts = (
        dom["rank_lock_violations"],
        dom["layer_separation_violations"],
        dom["tightness_failures"],
    )
    if problems or counts != (0, 0, 0):
        fails.append(f"{name} receipt {problems} {dom}")
    else:
        print(
            f"PASS {name} receipt locks={dom['locks']} "
            f"rank={counts[0]} layer={counts[1]} tight={counts[2]} "
            f"cross_check={dom['cross_check']}"
        )


def load_book():
    with BOOK.open(newline="") as f:
        rows = list(csv.DictReader(f))
    xs = [float(r["risk"]) for r in rows]
    ys = [float(r["cost"]) for r in rows]
    return xs, ys


def tie_grid(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = 60
    grid = np.column_stack([
        rng.integers(0, 6, size=n),
        rng.integers(0, 6, size=n),
    ]).astype(np.float64)
    return np.vstack([grid, grid[:15]])


def find_housing() -> Path | None:
    for path in HOUSING_CANDIDATES:
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest == HOUSING_SHA:
            return path
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="skip housing and abalone")
    args = parser.parse_args()
    fails: list[str] = []

    xs, ys = load_book()
    book_ranks = exact_rank_2d(xs, ys)
    book_sha = sha256_ranks(book_ranks)
    Xb = np.column_stack([xs, ys])
    if book_sha != BOOK_IDENTITY or not matches_cli(Xb, book_ranks):
        fails.append(f"book {book_sha}")
    else:
        print(f"PASS book identity {book_sha} n={len(book_ranks)}")

    listed = exact_rank_2d(list(xs), list(ys))
    if listed.tobytes() != np.ascontiguousarray(book_ranks, dtype=np.int32).tobytes():
        fails.append("list input diverged from numpy input")
    else:
        print("PASS book lists match numpy")

    try:
        exact_rank_2d([0.0, 1.0], [0.0])
        fails.append("length mismatch was accepted")
    except ValueError:
        print("PASS length mismatch rejected")

    for seed in range(12):
        grid = tie_grid(seed)
        got = exact_rank_2d(grid[:, 0], grid[:, 1])
        if not matches_cli(grid, got):
            fails.append(f"ties_seed_{seed}")
        else:
            print(f"PASS ties_seed_{seed} n={grid.shape[0]} identity={sha256_ranks(got)[:12]}")

    with tempfile.TemporaryDirectory(prefix="pgs_bind_") as td:
        out = Path(td) / "book.json"
        receipt = write_score_receipt(
            out,
            xs=xs,
            ys=ys,
            input_path=BOOK,
            columns=[{"name": "risk", "sense": "lower"}, {"name": "cost", "sense": "lower"}],
            pair_sieve_version=VERSION,
        )
        if sha256_ranks(exact_rank_2d(xs, ys)) != receipt["output"]["identity_sha256"]:
            fails.append("book receipt identity")
        check_zero_receipt(fails, "book", receipt, BOOK)

        if not args.offline:
            housing = find_housing()
            if housing is None:
                fails.append("rebuilt 10k housing csv missing or hash mismatch")
            else:
                matrix, _, _, _, _ = load_csv(housing, "median_income", "median_house_value")
                matrix = apply_senses(matrix, "higher", "higher")
                h_ranks = exact_rank_2d(matrix[:, 0], matrix[:, 1])
                h_sha = sha256_ranks(h_ranks)
                front = int(np.sum(h_ranks == 1))
                layers = int(np.max(h_ranks))
                if h_sha != HOUSING_IDENTITY or front != 31 or layers != 602 or not matches_cli(matrix, h_ranks):
                    fails.append(f"housing {h_sha} front={front} layers={layers}")
                else:
                    print(f"PASS housing identity {h_sha} front={front} layers={layers}")
                h_out = Path(td) / "housing.json"
                h_receipt = write_score_receipt(
                    h_out,
                    xs=matrix[:, 0],
                    ys=matrix[:, 1],
                    input_path=housing,
                    columns=[
                        {"name": "median_income", "sense": "higher"},
                        {"name": "median_house_value", "sense": "higher"},
                    ],
                    pair_sieve_version=VERSION,
                )
                check_zero_receipt(fails, "housing", h_receipt, housing)

            try:
                from sklearn.datasets import fetch_openml
                ab = fetch_openml(name="abalone", version=1, as_frame=False, parser="liac-arff")
                names = list(ab.feature_names)
                cols = np.column_stack([
                    -np.asarray(ab.data[:, names.index("Length")], dtype=np.float64),
                    -np.asarray(ab.data[:, names.index("Whole_weight")], dtype=np.float64),
                ])
                a_ranks = exact_rank_2d(cols[:, 0], cols[:, 1])
                a_sha = sha256_ranks(a_ranks)
                if a_sha != ABALONE_IDENTITY or not matches_cli(cols, a_ranks):
                    fails.append(f"abalone {a_sha}")
                else:
                    print(f"PASS abalone identity {a_sha} front={int(np.sum(a_ranks == 1))}")
                ab_csv = Path(td) / "abalone_two_col.csv"
                with ab_csv.open("w", newline="") as f:
                    w = csv.writer(f, lineterminator="\n")
                    w.writerow(["Length", "Whole_weight"])
                    for a, b in zip(-cols[:, 0], -cols[:, 1]):
                        w.writerow([repr(float(a)), repr(float(b))])
                a_receipt = write_score_receipt(
                    Path(td) / "abalone.json",
                    xs=cols[:, 0],
                    ys=cols[:, 1],
                    input_path=ab_csv,
                    columns=[
                        {"name": "Length", "sense": "higher"},
                        {"name": "Whole_weight", "sense": "higher"},
                    ],
                    pair_sieve_version=VERSION,
                )
                check_zero_receipt(fails, "abalone", a_receipt, ab_csv)
            except Exception as e:
                fails.append(f"abalone unavailable: {e}")

    if fails:
        for item in fails:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    print("GREEN: exact_rank_2d binding")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
