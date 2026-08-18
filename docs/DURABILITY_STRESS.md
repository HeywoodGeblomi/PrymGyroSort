# Durability Stress — Quantile vs Full under noise

**No break** on σ ∈ [0.05, 2.0] for temporal Jaccard, and **within-tick agree@top = 1.0** even at σ = 5.0 on this 2-D synthetic book.

| σ | J@top full | J@top q | agree@top (same X) | break |
|---:|---:|---:|---:|:---|
| 0.05 | 0.667 | 0.667 | 1.000 | no |
| 0.15 | 0.429 | 0.429 | 1.000 | no |
| 0.50 | 0.429 | 0.429 | 1.000 | no |
| 1.20 | 0.429 | 0.429 | 1.000 | no |
| 2.00 | 0.429 | 0.429 | 1.000 | no |

## Definitions (adversarial)

- **S@rank1**: `|prev_rank1 ∩ cur_rank1| / |prev_rank1|` — set survival, **not** “one dominant asset stays best 75% of the time.”
- **Jaccard**: `|A∩B|/|A∪B|` on symbol-ID sets (explicit set ops).
- **within-tick agree**: Jaccard between full and quantile fronts on the **same** `X`.

## Read

On this geometry, q=0.25 OR-quantile keeps the true top-frac (front points sit in an axis tail). That is **suite-specific**, not a universal proof.

## Non-claims

`promote_ready=false`. Not alpha. Kinetic “intercept” claims remain unmeasured.
