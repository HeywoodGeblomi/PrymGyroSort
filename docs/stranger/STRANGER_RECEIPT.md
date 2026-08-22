# STRANGER_RECEIPT.md — PGS-STR-001

**One stranger CSV. Identity + receipt. No new kernel.**

## Dataset

- Name: California Housing (two-column extract)
- File: `docs/stranger/california_housing_two_col.csv`
- SOURCE: see `docs/stranger/SOURCE.md`
- n = **20640** (full after filter; not a slice)
- x_col = median_income (sense = higher)
- y_col = median_house_value (sense = higher)

## Default run (χ off)

```bash
python3 python/pair_sieve_cli.py \
  --csv docs/stranger/california_housing_two_col.csv \
  --x-col median_income --y-col median_house_value \
  --x-sense higher --y-sense higher \
  --json --out docs/stranger/
```

### Report

| Field | Value |
|-------|-------|
| ok | true |
| n | 20640 |
| wall_ms | 5.9554 |
| front_size | 49 |
| identity_mode | fenwick_oracle |
| identity_ok | **true** |
| identity_sha256 | cf3ad281d81449ae396f2b0306fe41fd994f9fc94bac1f4ded44340a718ecb07 |
| strategy | Fenwick2D |
| promote_ready | false |
| version | 0.6.1-fix-now |

## Optional χ run (default remains off)

```bash
python3 python/pair_sieve_cli.py \
  --csv docs/stranger/california_housing_two_col.csv \
  --x-col median_income --y-col median_house_value \
  --x-sense higher --y-sense higher \
  --chi --json --out docs/stranger/chi_run
```

- chi_on = true
- chi_pick = 8849 (∈ front)
- ranks identity_sha256 **unchanged**
- chi_token = r_chi=-0.200 commit=passive

## Acceptance checklist

| ID | Pass |
|----|------|
| S1 | SOURCE.md names non-authored origin (1990 Census / Pace & Barry / Torgo / StatLib) |
| S2 | CLI run identity_ok=true, identity_mode=fenwick_oracle, strategy=Fenwick2D |
| S3 | Receipt on branch; book/listing/latency not used |
| S4 | gyro_rank.hpp / Photonic / Geblomi untouched |
| S5 | No UNIV/DAY language |

**Done. One stranger. Stop.**

No investment or trading claims.
