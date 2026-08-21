#!/usr/bin/env python3
"""GYR-SIEVE-003 Pair Sieve Product CLI. promote_ready=false. Fenwick-only."""
from __future__ import annotations

import argparse
import csv as _csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

VERSION = "0.6.0-pair-sieve-chi"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

from prefilter import apply_prefilter, run_falsifier, DEFAULT_Q


def die(code, msg, *, as_json=False):
    payload = {"ok": False, "error": msg, "exit_code": code, "version": VERSION, "promote_ready": False}
    print(json.dumps(payload) if as_json else f"[pair_sieve] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _load_rank():
    try:
        from prym_gyro import rank
        return rank
    except Exception as e:
        print(json.dumps({"error": "native_binding_unavailable", "detail": str(e)}), file=sys.stderr)
        raise SystemExit(3)


def validate_matrix(X, *, as_json=False):
    if not isinstance(X, np.ndarray) or X.ndim != 2 or X.shape[0] < 1 or X.shape[1] != 2:
        die(2, f"matrix must be (N,2); got {getattr(X, 'shape', None)}", as_json=as_json)
    X = np.ascontiguousarray(X, dtype=np.float64)
    if not np.isfinite(X).all():
        die(2, "non-finite values", as_json=as_json)
    return X


def load_matrix(path, n, *, as_json=False):
    p = Path(path)
    if not p.is_file():
        die(2, f"matrix not found: {path}", as_json=as_json)
    raw = np.fromfile(p, dtype=np.float64)
    if raw.size != n * 2:
        die(2, f"size mismatch {raw.size} vs {n * 2}", as_json=as_json)
    return validate_matrix(raw.reshape(n, 2), as_json=as_json)


def synthetic(n, seed):
    return np.ascontiguousarray(np.random.default_rng(seed).random((n, 2), dtype=np.float64))


def load_csv(path, x_col, y_col, *, as_json=False):
    p = Path(path)
    if not p.is_file():
        die(2, f"csv not found: {path}", as_json=as_json)
    with p.open(newline="") as f:
        reader = _csv.DictReader(f)
        if not reader.fieldnames:
            die(2, "csv has no header", as_json=as_json)
        fields = list(reader.fieldnames)

        def resolve(col):
            if col is None:
                return None
            if isinstance(col, int) or (isinstance(col, str) and str(col).isdigit()):
                idx = int(col)
                if idx < 0 or idx >= len(fields):
                    die(2, f"column index {idx} out of range", as_json=as_json)
                return fields[idx]
            if col not in fields:
                die(2, f"column {col!r} not in {fields}", as_json=as_json)
            return col

        x_name, y_name = resolve(x_col), resolve(y_col)
        rows = list(reader)
    if not rows:
        die(2, "csv empty", as_json=as_json)

    def is_num(v):
        try:
            float(v)
            return True
        except (TypeError, ValueError):
            return False

    if x_name is None or y_name is None:
        numeric = [n for n in fields if all(is_num(r.get(n, "")) for r in rows[: min(20, len(rows))])]
        if len(numeric) < 2:
            die(2, f"need 2 numeric cols; found {numeric}", as_json=as_json)
        x_name = x_name or numeric[0]
        y_name = y_name or (numeric[1] if numeric[1] != x_name else numeric[0])
    xs, ys = [], []
    for i, r in enumerate(rows):
        try:
            xv, yv = float(r[x_name]), float(r[y_name])
        except (KeyError, TypeError, ValueError) as e:
            die(2, f"row {i}: {e}", as_json=as_json)
        if not (np.isfinite(xv) and np.isfinite(yv)):
            die(2, f"row {i}: NaN/Inf", as_json=as_json)
        xs.append(xv)
        ys.append(yv)
    X = np.ascontiguousarray(np.column_stack([xs, ys]), dtype=np.float64)
    return X, x_name, y_name, rows, fields


def apply_senses(X, x_sense, y_sense):
    out = X.copy()
    if x_sense == "higher":
        out[:, 0] = -out[:, 0]
    if y_sense == "higher":
        out[:, 1] = -out[:, 1]
    return out


def ranks_sha256(ranks):
    return hashlib.sha256(np.ascontiguousarray(ranks, dtype=np.int32).tobytes()).hexdigest()


def run_pair_sieve(X, k=1, *, prefilter=None, prefilter_q=DEFAULT_Q, chi=False, chi_seed=0, as_json=False):
    rank_fn = _load_rank()
    from chi_pick import chi_pick
    X_full = validate_matrix(X, as_json=as_json)
    n_full = int(X_full.shape[0])
    if k < 1:
        die(1, "k must be >= 1", as_json=as_json)
    n_dropped = 0
    if prefilter:
        X, _ = apply_prefilter(X_full, name=prefilter, q=prefilter_q)
        n_dropped = int(n_full - X.shape[0])
        if X.shape[0] < 1:
            die(2, "prefilter dropped all rows", as_json=as_json)
        X = validate_matrix(X, as_json=as_json)
    else:
        X = X_full
    n = int(X.shape[0])
    t0 = time.perf_counter()
    ranks = np.ascontiguousarray(rank_fn(X, memory_pressure=False), dtype=np.int32)
    wall_ms = (time.perf_counter() - t0) * 1e3
    ranks_ref = np.ascontiguousarray(rank_fn(X, memory_pressure=False), dtype=np.int32)
    identity_ok = bool(np.array_equal(ranks, ranks_ref))
    sha = ranks_sha256(ranks)
    front_size = int(np.sum(ranks == 1))
    F = [int(i) for i in np.flatnonzero(ranks <= k)]
    report = {
        "ok": True,
        "version": VERSION,
        "n": n,
        "wall_ms": round(wall_ms, 4),
        "front_size": front_size,
        "k": int(k),
        "identity_sha256": sha,
        "identity_ok": identity_ok,
        "identity_mode": "fenwick_repeat",
        "strategy": "Fenwick2D",
        "promote_ready": False,
    }
    if prefilter:
        report.update(
            prefilter=prefilter,
            prefilter_q=float(prefilter_q),
            n_full=n_full,
            n_dropped=n_dropped,
            n_survivors=n,
        )
    if chi:
        try:
            chi_result = chi_pick(F, seed=chi_seed)
            pick = chi_result["pick"]
            if pick not in F:
                die(4, f"chi pick {pick} not in F", as_json=as_json)
            if ranks_sha256(ranks) != sha:
                die(4, "chi path mutated ranks", as_json=as_json)
            report.update(
                chi_on=True,
                chi_pick=int(pick),
                chi_token=chi_result["chi_token"],
                chi_seed=int(chi_seed),
            )
        except ValueError as e:
            die(4, str(e), as_json=as_json)
    return report, ranks, X


def main():
    ap = argparse.ArgumentParser(description=f"Pair sieve product {VERSION}")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--csv", default=None, help="CSV with header (product path)")
    ap.add_argument("--x-col", default=None, help="x column name or 0-based index")
    ap.add_argument("--y-col", default=None, help="y column name or 0-based index")
    ap.add_argument("--x-sense", default="lower", choices=["lower", "higher"])
    ap.add_argument("--y-sense", default="lower", choices=["lower", "higher"])
    ap.add_argument("--matrix", default=None)
    ap.add_argument("--n", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--prefilter", default="off", choices=["off", "or_quantile", "prym"])
    ap.add_argument("--q", type=float, default=DEFAULT_Q)
    ap.add_argument("--chi", action="store_true", help="optional irreversible pick among undominated set (off by default)")
    ap.add_argument("--chi-seed", type=int, default=0)
    ap.add_argument("--falsifier", action="store_true")
    ap.add_argument(
        "--prove",
        action="store_true",
        help="P3: S1 identity (N=1e5) + both falsifiers; exit 0 iff prove_ok",
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    as_json = bool(args.json)

    if args.version:
        print(json.dumps({"version": VERSION, "promote_ready": False}) if as_json else VERSION)
        return 0
    if args.falsifier:
        fname = "prym" if args.prefilter == "prym" else "or_quantile"
        result = run_falsifier(q=float(args.q), name=fname)
        print(json.dumps(result, indent=2) if as_json else result)
        return 0 if result["falsifier_ok"] else 9

    if args.prove:
        results = {}
        fq = run_falsifier(q=float(args.q), name="or_quantile")
        results["or_quantile"] = bool(fq.get("falsifier_ok"))
        fp = run_falsifier(q=float(args.q), name="prym")
        results["prym"] = bool(fp.get("falsifier_ok"))
        try:
            X = synthetic(100_000, 42)
            report, ranks, _ = run_pair_sieve(X, k=1, as_json=as_json)
            results["identity_n1e5"] = bool(report.get("identity_ok"))
            results["n"] = int(report.get("n", 0))
            results["wall_ms"] = report.get("wall_ms")
            results["identity_sha256"] = report.get("identity_sha256")
        except SystemExit:
            results["identity_n1e5"] = False
        prove_ok = all(
            [
                results.get("or_quantile"),
                results.get("prym"),
                results.get("identity_n1e5"),
            ]
        )
        out = {
            "ok": prove_ok,
            "prove_ok": prove_ok,
            "version": VERSION,
            "promote_ready": False,
            "checks": results,
        }
        print(json.dumps(out, indent=2) if as_json else out)
        return 0 if prove_ok else 9

    try:
        csv_rows = csv_fields = None
        x_name = y_name = None
        if args.csv:
            X, x_name, y_name, csv_rows, csv_fields = load_csv(
                args.csv, args.x_col, args.y_col, as_json=as_json
            )
            source = f"csv:{args.csv}"
            X = apply_senses(X, args.x_sense, args.y_sense)
        elif args.matrix:
            X = load_matrix(args.matrix, args.n, as_json=as_json)
            source, x_name, y_name = str(args.matrix), "0", "1"
            X = apply_senses(X, args.x_sense, args.y_sense)
        else:
            if args.n < 1 or args.n > 5_000_000:
                die(1, f"n out of range: {args.n}", as_json=as_json)
            X = synthetic(args.n, args.seed)
            source, x_name, y_name = f"synthetic_seed={args.seed}", "0", "1"
            X = apply_senses(X, args.x_sense, args.y_sense)

        pf = None if args.prefilter == "off" else args.prefilter
        report, ranks, Xp = run_pair_sieve(
            X,
            k=args.k,
            prefilter=pf,
            prefilter_q=float(args.q),
            chi=args.chi,
            chi_seed=args.chi_seed,
            as_json=as_json,
        )
        report.update(
            source=source,
            x_col=x_name,
            y_col=y_name,
            x_sense=args.x_sense,
            y_sense=args.y_sense,
        )

        if as_json:
            print(json.dumps(report))
        else:
            print(
                f"[pair_sieve] n={report['n']} wall_ms={report['wall_ms']:.3f} "
                f"front_size={report['front_size']} identity_ok={report['identity_ok']} "
                f"strategy={report['strategy']} promote_ready=false"
            )

        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            np.save(out / "ranks.npy", ranks)
            (out / "report.json").write_text(json.dumps(report, indent=2))
            rank1 = set(int(i) for i in np.flatnonzero(np.asarray(ranks) == 1))
            front_path = out / "front.csv"
            chi_pick_idx = report.get("chi_pick") if report.get("chi_on") else None
            if csv_rows is not None and not pf:
                fields = list(csv_fields) + ["rank"]
                if chi_pick_idx is not None:
                    fields.append("chi_pick")
                with front_path.open("w", newline="") as f:
                    w = _csv.DictWriter(f, fieldnames=fields)
                    w.writeheader()
                    for i, row in enumerate(csv_rows):
                        if i in rank1:
                            r = dict(row)
                            r["rank"] = 1
                            if chi_pick_idx is not None:
                                r["chi_pick"] = 1 if i == int(chi_pick_idx) else 0
                            w.writerow(r)
            else:
                with front_path.open("w", newline="") as f:
                    w = _csv.writer(f)
                    hdr = ["idx", "x", "y", "rank"]
                    if chi_pick_idx is not None:
                        hdr.append("chi_pick")
                    w.writerow(hdr)
                    for i in sorted(rank1):
                        row = [i, float(Xp[i, 0]), float(Xp[i, 1]), 1]
                        if chi_pick_idx is not None:
                            row.append(1 if i == int(chi_pick_idx) else 0)
                        w.writerow(row)

        return 0 if report["identity_ok"] else 4
    except SystemExit:
        raise
    except Exception as e:
        print(
            json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}", "exit_code": 3, "promote_ready": False})
            if as_json
            else f"[pair_sieve] ERROR: {e}",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
