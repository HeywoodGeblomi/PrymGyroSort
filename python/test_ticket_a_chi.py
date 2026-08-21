#!/usr/bin/env python3
"""GYR-SIEVE-002 Ticket A: real ChiState import, S5/S6, determinism."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from vendor.chi_primitive import ChiState
from chi_pick import chi_pick
import chi_pick as cp

def main() -> int:
    fails = 0
    st = ChiState(chi=1)
    assert hasattr(st, "commit") and hasattr(st, "safe_token") and hasattr(st, "reveal")
    st.commit()
    _ = st.safe_token()
    print("PASS A1: ChiState from vendor")

    src = Path(cp.__file__).read_text()
    assert "class ChiState" not in src
    print("PASS A1: no local ChiState in chi_pick.py")

    try:
        chi_pick([])
        fails += 1
        print("FAIL |F|==0")
    except ValueError:
        print("PASS S6 |F|==0")

    assert chi_pick([42], 0)["pick"] == 42
    print("PASS S6 |F|==1")

    F = [10, 3, 7, 100, 5]
    r = chi_pick(F, 7)
    assert r["pick"] in F
    print(f"PASS S6 pick={r['pick']} token={r['chi_token']}")

    assert chi_pick(F, 99)["pick"] == chi_pick(F, 99)["pick"]
    print("PASS A2 determinism")

    t0 = chi_pick(F, 0)["chi_token"]
    t1 = chi_pick(F, 1)["chi_token"]
    print(f"INFO tokens seed0={t0} seed1={t1}")
    print(f"fails={fails}")
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
