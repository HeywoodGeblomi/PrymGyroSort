#!/usr/bin/env python3
"""Invariants over tiers.json + hrp_research.json. Does NOT assert seriation≡ranks."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="work/tiers.json")
    ap.add_argument("--hrp", default="work/hrp_research.json")
    ap.add_argument("--tail", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    checks = []
    try:
        tiers = json.loads(Path(args.tiers).read_text())
        hrp = json.loads(Path(args.hrp).read_text())
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 2

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("tiers_ok", tiers.get("ok") is True)
    br = tiers.get("circuit_breaker") or {}
    add("breaker_clear", not br.get("tripped", True), str(br.get("reasons")))
    tier1 = tiers.get("tier1_indices") or []
    add("tier1_nonempty", len(tier1) > 0, f"size={len(tier1)}")
    add("hrp_ok", hrp.get("ok") is True)
    w = hrp.get("weights") or []
    idx = hrp.get("tier1_indices") or []
    add("hrp_index_align", idx == tier1, f"hrp={len(idx)} tier1={len(tier1)}")
    add("weights_len", len(w) == len(tier1), f"w={len(w)}")
    if w:
        s = sum(w)
        add("weight_sum_1", abs(s - 1.0) < 1e-6, f"sum={s}")
        add("weights_nonneg", all(x >= -1e-12 for x in w), f"min={min(w)}")
    else:
        add("weight_sum_1", False, "empty")
        add("weights_nonneg", False, "empty")
    add("membership", set(idx).issubset(set(tier1)) if tier1 else False)

    if args.tail:
        try:
            tail = json.loads(Path(args.tail).read_text())
            add("tail_ok", tail.get("ok") is True)
            add("tail_has_shocks", bool(tail.get("shocks")))
            for row in tail.get("shocks") or []:
                if abs(sum(row.get("weights") or []) - 1.0) > 1e-5:
                    add("tail_weight_sum", False, f"sev={row.get('severity')}")
                    break
            else:
                if tail.get("shocks"):
                    add("tail_weight_sum", True)
        except Exception as e:
            add("tail_ok", False, str(e))

    ok = all(c["ok"] for c in checks)
    payload = {
        "ok": ok,
        "checks": checks,
        "promote_ready": False,
        "note": "Does not assert HRP seriation ≡ sieve ranks (different geometries)",
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for c in checks:
            print(
                f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}"
                + (f"  {c['detail']}" if c["detail"] and not c["ok"] else "")
            )
        print(f"[verify_hrp_export] {'PASS' if ok else 'FAIL'} promote_ready=false")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
