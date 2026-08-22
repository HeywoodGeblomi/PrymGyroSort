# STRANGER_RECEIPT.md — PGS-STR-001

**One stranger CSV. Identity + receipt. No new kernel.**

## Dataset

- Name: California Housing (two-column extract, documented ≥10k slice)
- Producer: `docs/stranger/filter_california_housing.py` (pulls SOURCE.md URL → writes the two-col file)
- File produced: `docs/stranger/california_housing_two_col.csv`
- n = **10000** (first 10k after filter; full recoverable N=20640)
- x_col = median_income (sense = higher)
- y_col = median_house_value (sense = higher)
- After running the filter: `wc -l docs/stranger/california_housing_two_col.csv` = 10001

## Default run (χ off)

```bash
python3 docs/stranger/filter_california_housing.py
python3 python/pair_sieve_cli.py \
  --csv docs/stranger/california_housing_two_col.csv \
  --x-col median_income --y-col median_house_value \
  --x-sense higher --y-sense higher \
  --json --out docs/stranger/
```

### Report (measured on the file produced by the filter)

| Field | Value |
|-------|-------|
| ok | true |
| n | 10000 |
| wall_ms | 2.8679 |
| front_size | 32 |
| identity_mode | fenwick_oracle |
| identity_ok | **true** |
| identity_sha256 | 3a94ab3104a0f77f7378639f08b816ca7f76b9b00bde432542c7afd682bdb417 |
| strategy | Fenwick2D |
| promote_ready | false |
| version | 0.6.1-fix-now |

## Optional χ run (default remains off)

Re-run with `--chi` yields pick ∈ front and identical identity_sha256. Default χ remains off.

## Acceptance checklist

| ID | Pass |
|----|------|
| S1 | SOURCE.md names non-authored origin (1990 Census / Pace & Barry / Torgo / StatLib) |
| S2 | CLI run on the file produced by the filter: identity_ok=true, fenwick_oracle, Fenwick2D; n matches |
| S3 | Receipt on branch; book/listing/latency not used |
| S4 | gyro_rank.hpp / Photonic / Geblomi untouched |
| S5 | No UNIV/DAY language |

**Done. One stranger. Stop.**

No investment or trading claims.
