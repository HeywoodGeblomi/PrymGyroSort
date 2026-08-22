# NON_CLAIMS — PrymGyroSort Sealed Front Product

## What this product is

**Isolation + proof.** Two numeric scores in; the undominated set out; a SHA-256 of the rank vector so a re-run of Fenwick yields the same bits; offline `verify_bundle` pass/fail. That is the sealed-front job. That is enough.

**`promote_ready=true` for this job only** when `identity_ok` and `identity_mode=fenwick_oracle`. The ranker library itself is not promoted as a universal ranking OS.

## Score Contract (DOM-SC-001)

Optional structured definition of the two axes (name, sense, unit, procedure id) with a canonical hash embedded in the report. When present, `verify_bundle` recomputes and matches the hash (V5). When absent, verify stays soft (backward compatible). A Score Contract is a **label of how the two numbers were meant to be computed** — not a proof that the world matches the label, not certainty, not a third objective.

## Front Diff (DOM-FD-001)

`front_diff` compares two verified seals and reports which front members entered, left, or stayed. Both inputs must pass `verify_bundle` first. It is **change detection on two seals**, not a re-rank, not a forecast, not a third objective.

## What this product is not

1. **Not a predictive model.** Structural weak-dominance isolation, not a forecast.
2. **Not investment advice.** No recommendation, no allocation, no portfolio construction claim.
3. **Not a trading system / order router.** No live execution, no alpha.
4. **Not multi-objective NSGA / evolutionary Pareto.** Exact two-score undominated set only; no population search.
5. **Not ownership of Lyapunov theorems.** Optional path-local residual bands do not establish global exponents.
6. **Not a second ranking kernel.** Exact M=2 ranking is Fenwick-only (GyroRank v0.2). LowAux2D and Scan2D are not shipped. The sealed front is a product wrapper around the library.
7. **Not M≥3 exact ranking.** Two columns. Period.
8. **Not a universal ranking OS.** `promote_ready=true` applies only to the sealed-front job defined above.

## χ (optional)

When `--chi` is on, one index is selected from the undominated front via `chi_pick`: ChiState **commit + reveal** tape is mixed into the index hash (NRC-THM-001-C). Ranks are not rewritten. Optional irreversible pick among undominated rows — not “AI allocation.”

- Default path uses the dynamic commit/reveal tape; a pure hash of sorted F (no ChiState) is the **rejected test double**.
- `--chi` is off by default.
- Spec: [non-reducible-commitment docs/THEOREM.md](https://github.com/HeywoodGeblomi/non-reducible-commitment/blob/main/docs/THEOREM.md) (T1–T5).

## Language to avoid

- “LowAux2D”, “N≥65536 → LowAux2D”
- “global Lyapunov”, “spectrum certificate”
- “alpha”, “guaranteed profitable”
- “AI allocation”
- “certainty” from ranking possible vs plausible
