# Kinetic A/B Match

Baseline (static + q=0.25) vs Kinetic (velocity transform + same q).

| arm | J@top | S@top | agree@top vs full static |
|:---|---:|---:|---:|
| baseline | 0.429 | 0.600 | 1.000 |
| kinetic | 0.429 | 0.600 | 1.000 |

**Verdict:** FAIL: no durability improvement over baseline (`ship=False`)

Sweep (α,β ∈ {0.25,0.5,1.0}, σ ∈ {0.15,0.5,1.0}): **all ship=False**.

## Ship rule

agree@top ≥ 0.90 **and** (S@top or J@top) strictly greater than baseline.

## Non-claims

Feature transform only. Not prediction alpha. Core frozen. `promote_ready=false`.

```bash
python3 python/test_kinetic_match.py --alpha 0.5 --beta 0.5 --sigma 0.15
```
