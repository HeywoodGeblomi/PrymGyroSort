# NON_CLAIMS — PrymGyroSort Pair Sieve Product

## What this product is

**Isolation + proof.** Two numeric scores in; the undominated set out; a SHA-256 of the rank vector so a re-run of Fenwick yields the same bits. That is the claim. That is enough.

## What this product is not

1. **Not a predictive model.** Structural weak-dominance isolation, not a forecast.
2. **Not a trading system / order router.** No live execution, no alpha.
3. **Not ownership of Lyapunov theorems.** Optional path-local residual bands do not establish global exponents.
4. **Not a second ranking kernel.** Exact M=2 ranking is Fenwick-only (GyroRank v0.2). LowAux2D and Scan2D are not shipped.
5. **Not M≥3 exact ranking.** Two columns. Period.
6. **`promote_ready = false`.** Always. The identity hash is the proof surface.

## χ (optional)

When `--chi` is on, one index is selected from the undominated front via `chi_pick`: ChiState **commit + reveal** tape is mixed into the index hash (NRC-THM-001-C). Ranks are not rewritten. Optional irreversible pick among undominated rows — not “AI allocation.”

- Default path uses the dynamic commit/reveal tape; a pure hash of sorted F (no ChiState) is the **rejected test double**.
- `--chi` is off by default. `promote_ready=false`.
- Spec: [non-reducible-commitment docs/THEOREM.md](https://github.com/HeywoodGeblomi/non-reducible-commitment/blob/main/docs/THEOREM.md) (T1–T5).

## Language to avoid

- “LowAux2D”, “N≥65536 → LowAux2D”
- “global Lyapunov”, “spectrum certificate”
- “alpha”, “guaranteed profitable"
