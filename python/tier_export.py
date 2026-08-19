#!/usr/bin/env python3
"""Circuit breaker + immutable tier export. promote_ready=false."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

VERSION = "0.1.5.1"


def evaluate_breaker(
    report: dict[str, Any],
    *,
    n_min: int = 50,
    n_max_frac: float = 0.90,
    require_rank1: bool = True,
) -> dict[str, Any]:
    reasons: list[str] = []
    if not report.get("ok", False):
        reasons.append("sieve_report_not_ok")
    n = int(report.get("n", 0))
    n_prime = int(report.get("n_prime", 0))
    min_rank = report.get("min_rank")
    if n < 1:
        reasons.append("n_invalid")
    if n_prime < n_min:
        reasons.append(f"n_prime_below_min:{n_prime}<{n_min}")
    if n > 0 and n_prime > n_max_frac * n:
        reasons.append(f"n_prime_above_max_frac:{n_prime}>{n_max_frac}*n")
    if require_rank1 and min_rank is not None and int(min_rank) != 1:
        reasons.append(f"no_rank1_min_rank={min_rank}")
    return {
        "tripped": len(reasons) > 0,
        "reasons": reasons,
        "n": n,
        "n_prime": n_prime,
        "n_min": n_min,
        "n_max_frac": n_max_frac,
        "require_rank1": require_rank1,
    }


def build_tiers(report: dict[str, Any], ranks: np.ndarray | None = None) -> dict[str, Any]:
    n = int(report["n"])
    top_indices = [int(i) for i in report.get("top_indices", [])]
    top_ranks = [int(r) for r in report.get("top_ranks", [])]
    tiers: dict[str, list[int]] = {}
    if ranks is not None:
        ranks = np.asarray(ranks, dtype=np.int32).reshape(-1)
        if ranks.shape[0] != n:
            raise ValueError(f"ranks length {ranks.shape[0]} != n {n}")
        valid = ranks < 10**8
        max_r = int(ranks[valid].max()) if np.any(valid) else 1
        for layer in range(1, min(max_r, 32) + 1):
            idx = np.flatnonzero(ranks == layer).tolist()
            if idx:
                tiers[f"rank_{layer}"] = [int(i) for i in idx]
    else:
        by_rank: dict[int, list[int]] = {}
        for i, r in zip(top_indices, top_ranks):
            by_rank.setdefault(int(r), []).append(int(i))
        for r in sorted(by_rank):
            tiers[f"rank_{r}"] = by_rank[r]
    tier1 = tiers.get("rank_1", [])
    return {
        "ok": True,
        "version": VERSION,
        "immutable": True,
        "promote_ready": False,
        "n": n,
        "n_prime": int(report.get("n_prime", 0)),
        "path": report.get("path"),
        "source": report.get("source"),
        "tier1_indices": tier1,
        "tier1_size": len(tier1),
        "tiers": tiers,
        "top_indices": top_indices,
        "top_ranks": top_ranks,
        "min_rank": int(report.get("min_rank", 1)),
        "ms": report.get("ms"),
        "non_claims": [
            "Structural tier indices only",
            "Not portfolio weights",
            "Not a trading signal",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Circuit breaker + tier export")
    ap.add_argument("--report", required=True)
    ap.add_argument("--ranks", default=None)
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--n-min", type=int, default=50)
    ap.add_argument("--n-max-frac", type=float, default=0.90)
    ap.add_argument("--allow-no-rank1", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report_path = Path(args.report)
    if not report_path.is_file():
        print(json.dumps({"ok": False, "error": f"report not found: {report_path}"}), file=sys.stderr)
        return 2
    report = json.loads(report_path.read_text())
    br = evaluate_breaker(
        report,
        n_min=args.n_min,
        n_max_frac=args.n_max_frac,
        require_rank1=not args.allow_no_rank1,
    )
    ranks = np.load(args.ranks) if args.ranks else None
    try:
        tiers = build_tiers(report, ranks)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2
    tiers["circuit_breaker"] = br
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "tiers.json"
    out_path.write_text(json.dumps(tiers, indent=2))
    (out_dir / "tiers.IMMUTABLE").write_text(
        f"immutable tier export\nversion={VERSION}\ntripped={br['tripped']}\n"
    )
    if br["tripped"]:
        err = {
            "ok": False,
            "error": "circuit_breaker_tripped",
            "reasons": br["reasons"],
            "tiers_path": str(out_path),
            "promote_ready": False,
        }
        print(json.dumps(err) if args.json else f"[tier_export] BREAKER {br['reasons']}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "tiers_path": str(out_path),
                    "tier1_size": tiers["tier1_size"],
                    "circuit_breaker": br,
                }
            )
        )
    else:
        print(
            f"[tier_export] {VERSION} tier1={tiers['tier1_size']} "
            f"n'={tiers['n_prime']} breaker=OK → {out_path}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
