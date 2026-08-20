#!/usr/bin/env python3
"""
Track 2 χ pick — GYR-SIEVE-001 §4

χ sees the front F only. Never writes ranks. Never calls ranking.
Deterministic given the same F and documented seed/tape.

Tape: sorted(F) + seed → SHA256 → index into F.
Also records a ChiState commitment token for the sidecar report.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class ChiState:
    """Minimal non-reducible commitment bit (vendored spirit of non-reducible-commitment)."""
    chi: int = 1
    flips: int = 0

    def commit(self) -> int:
        self.chi ^= 1
        self.flips += 1
        return self.chi

    def polarity(self) -> float:
        return 1.0 if self.chi == 1 else -1.0

    def safe_token(self) -> str:
        return f"chi_flips={self.flips} polarity={self.polarity():+.0f}"


def chi_pick(F: Sequence[int], seed: int = 0) -> dict:
    """
    Select one index from F.
    - |F|==0 → fail-closed (raise ValueError)
    - |F|==1 → that id
    - else   → deterministic index from SHA256(seed || sorted(F))
    Returns {pick, chi_token, chi_on}.
    """
    F_list = [int(x) for x in F]
    if len(F_list) == 0:
        raise ValueError("chi_pick fail-closed: |F|==0, no row to invent")
    if len(F_list) == 1:
        st = ChiState()
        st.commit()  # one irreversible commit for the record
        return {"pick": F_list[0], "chi_token": st.safe_token(), "chi_on": True}

    # Deterministic tape: seed + sorted F bytes
    sorted_F = sorted(F_list)
    h = hashlib.sha256()
    h.update(int(seed).to_bytes(8, "little", signed=True))
    h.update(b"," .join(str(i).encode() for i in sorted_F))
    digest = h.digest()
    idx = int.from_bytes(digest[:8], "little") % len(sorted_F)
    pick = sorted_F[idx]

    st = ChiState()
    # Documented: number of commits = (seed % 3) + 1 so parity is part of the tape
    for _ in range((abs(int(seed)) % 3) + 1):
        st.commit()

    return {"pick": pick, "chi_token": st.safe_token(), "chi_on": True}
