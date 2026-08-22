#!/usr/bin/env python3
"""
NRC-THM-001-C — Consumer falsifier for χ pick in PrymGyroSort.

C1: Default --chi path calls commit + reveal (tape moves).
C2: Hash-only double (SHA256(seed ‖ sorted F) only) FAILS the tape contract.
C3: Real path: pick ∈ F, ranks not mutated by chi_pick.

If both real and hash-only pass, χ was not used. Do not merge.
GyroRank / Photonic / Geblomi untouched. --chi remains default off.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from chi_pick import chi_pick  # noqa: E402
import chi_pick as cp  # noqa: E402


def hash_only_pick(F, seed: int = 0) -> dict:
    """
    Rejected test double for C2.
    SHA256(seed ‖ sorted F) only — no ChiState, no commit, no reveal, no token.
    Must NOT be the default --chi path.
    """
    F_list = [int(x) for x in F]
    if len(F_list) == 0:
        raise ValueError("hash_only_pick fail-closed: |F|==0")
    sorted_F = sorted(F_list)
    if len(sorted_F) == 1:
        return {"pick": sorted_F[0], "chi_token": None, "chi_on": False, "hash_only": True}
    h = hashlib.sha256()
    h.update(int(seed).to_bytes(8, "little", signed=True))
    h.update(b",".join(str(i).encode() for i in sorted_F))
    # deliberately NO token / NO ChiState tape
    idx = int.from_bytes(h.digest()[:8], "little") % len(sorted_F)
    return {"pick": sorted_F[idx], "chi_token": None, "chi_on": False, "hash_only": True}


class TestC1RealTape(unittest.TestCase):
    """C1: Default chi_pick path calls commit + reveal (or equivalent moving token)."""

    def test_source_contains_commit_and_reveal(self):
        src = Path(cp.__file__).read_text()
        self.assertIn("st.commit()", src)
        self.assertIn("st.reveal()", src)
        self.assertIn("safe_token", src)
        self.assertNotIn("class ChiState", src)  # must come from vendor

    def test_token_comes_from_reveal(self):
        r = chi_pick([10, 3, 7, 100, 5], seed=7)
        self.assertIn("r_chi=", r["chi_token"])
        self.assertTrue(r["chi_on"])

    def test_token_varies_with_commit_schedule(self):
        F = [10, 3, 7, 100, 5]
        # seed 0 → 1 commit (odd); seed 1 → 2 commits (even) → different polarity/token
        tokens = {chi_pick(F, s)["chi_token"] for s in (0, 1, 2, 3)}
        self.assertGreater(len(tokens), 1, "tape must move with commit count")


class TestC2HashOnlyFails(unittest.TestCase):
    """
    C2: Inject HashOnly / pure SHA256(seed ‖ sorted F): the consumer test MUST FAIL.

    Real path satisfies the tape contract (token from safe_token after commit+reveal).
    Hash-only has no ChiState tape → fails the same contract.
    """

    def test_hash_only_has_no_chi_token_from_reveal(self):
        F = [10, 3, 7, 100, 5]
        pure = hash_only_pick(F, seed=7)
        self.assertTrue(pure.get("hash_only"))
        self.assertIsNone(pure.get("chi_token"))
        # Contract that real path must satisfy and hash-only cannot:
        # chi_token must be a ChiState safe_token string containing r_chi=
        self.assertNotIsInstance(pure.get("chi_token"), str)

    def test_hash_only_fails_tape_contract_assertion(self):
        """Named failure: hash-only does not satisfy 'token from reveal'."""
        F = [10, 3, 7, 100, 5]
        real = chi_pick(F, seed=7)
        pure = hash_only_pick(F, seed=7)

        def requires_reveal_token(result: dict) -> None:
            tok = result.get("chi_token")
            assert isinstance(tok, str) and "r_chi=" in tok, (
                "consumer requires chi_token from ChiState.safe_token after commit+reveal"
            )

        # Real path passes the contract
        requires_reveal_token(real)

        # Hash-only MUST fail the same contract
        with self.assertRaises(AssertionError):
            requires_reveal_token(pure)

    def test_hash_only_insensitive_to_chi_state(self):
        """Hash-only pick is a pure function of (F, seed); no internal χ."""
        F = [4, 1, 9, 2]
        picks = {hash_only_pick(F, seed=0)["pick"] for _ in range(5)}
        self.assertEqual(len(picks), 1)


class TestC3RealPathInvariants(unittest.TestCase):
    """C3: Real path — pick ∈ F, fail-closed edges, determinism. Ranks never seen by chi_pick."""

    def test_empty_F_fails_closed(self):
        with self.assertRaises(ValueError):
            chi_pick([])

    def test_singleton(self):
        self.assertEqual(chi_pick([42], 0)["pick"], 42)

    def test_pick_in_F(self):
        F = [10, 3, 7, 100, 5]
        for seed in range(8):
            r = chi_pick(F, seed)
            self.assertIn(r["pick"], F)

    def test_determinism(self):
        F = [10, 3, 7, 100, 5]
        self.assertEqual(chi_pick(F, 99)["pick"], chi_pick(F, 99)["pick"])
        self.assertEqual(chi_pick(F, 99)["chi_token"], chi_pick(F, 99)["chi_token"])

    def test_chi_pick_does_not_mutate_or_accept_ranks(self):
        # chi_pick never takes a ranks argument and never returns ranks.
        r = chi_pick([10, 3, 7], seed=1)
        self.assertNotIn("ranks", r)
        self.assertIn("pick", r)
        src = Path(cp.__file__).read_text()
        self.assertIn("Never writes ranks", src)
        import inspect
        sig = inspect.signature(chi_pick)
        self.assertNotIn("ranks", sig.parameters)
        self.assertIn("F", sig.parameters)
        self.assertIn("seed", sig.parameters)


class TestC4PinAndDefaultOff(unittest.TestCase):
    def test_pin_documented(self):
        pin = (ROOT / "vendor" / "chi_primitive" / "PIN.txt").read_text()
        self.assertIn("HeywoodGeblomi/non-reducible-commitment", pin)
        self.assertRegex(pin, r"[0-9a-f]{40}")

    def test_cli_chi_default_off_in_source(self):
        cli = (ROOT / "pair_sieve_cli.py").read_text()
        self.assertIn('action="store_true"', cli)
        self.assertIn("--chi", cli)
        # default off: store_true means False unless flag present
        self.assertIn("help=", cli)


if __name__ == "__main__":
    unittest.main()
