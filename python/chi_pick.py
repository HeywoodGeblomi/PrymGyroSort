#!/usr/bin/env python3
"""
GYR-SIEVE-003 P4 — χ as product pick (optional irreversible pick among undominated).

χ sees the front F only. Never writes ranks. Never calls ranking.
Copy: optional irreversible pick among the undominated set — not "AI allocation."

Vendored ChiState from HeywoodGeblomi/non-reducible-commitment
  Pin SHA: 7cd60a7ac325d78f536628f090ea8bc57f9ae010
  Path: python/vendor/chi_primitive/

Documented tape (P4):
  Sort F ascending. ChiState(chi=1).
  Commit exactly (abs(seed) % 3) + 1 times.
  Call reveal() once so r_chi is non-zero and drives the token.
  index = int.from_bytes(SHA256(seed_bytes || sorted_F_bytes || safe_token())[:8], 'little') % |F|.
  pick = sorted(F)[index]. Same F + same seed → same pick.
  safe_token() is report chi_token; raw χ never in JSON.

|F|==0 fail-closed. |F|==1 returns that id (still commits + reveal for the record).
"""
from __future__ import annotations

import hashlib
from typing import Sequence

from vendor.chi_primitive import ChiState  # pin 7cd60a7ac325d78f536628f090ea8bc57f9ae010


def chi_pick(F: Sequence[int], seed: int = 0) -> dict:
    F_list = [int(x) for x in F]
    if len(F_list) == 0:
        raise ValueError("chi_pick fail-closed: |F|==0, no row to invent")

    sorted_F = sorted(F_list)
    st = ChiState(chi=1)
    n_commits = (abs(int(seed)) % 3) + 1
    for _ in range(n_commits):
        st.commit()
    # P4: reveal so the tape is not a constant safe_token
    st.reveal()

    token = st.safe_token()

    if len(sorted_F) == 1:
        return {"pick": sorted_F[0], "chi_token": token, "chi_on": True}

    h = hashlib.sha256()
    h.update(int(seed).to_bytes(8, "little", signed=True))
    h.update(b",".join(str(i).encode() for i in sorted_F))
    h.update(token.encode("utf-8"))
    idx = int.from_bytes(h.digest()[:8], "little") % len(sorted_F)
    return {"pick": sorted_F[idx], "chi_token": token, "chi_on": True}
