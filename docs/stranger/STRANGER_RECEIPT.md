# STRANGER_RECEIPT.md — PGS-STR-001

**One stranger CSV. Identity + receipt. No new kernel.**

## Dataset

- Name: California Housing (two-column extract, documented slice)
- File: `docs/stranger/california_housing_two_col.csv`
- SOURCE: see `docs/stranger/SOURCE.md`
- n = **10000** (documented first-10k slice after filter; full recoverable N=20640 from cited URL)
- x_col = median_income (sense = higher)
- y_col = median_house_value (sense = higher)
- `wc -l` on committed CSV = 10001 (header + 10000 data rows)

## Default run (χ off)

```bash
python3 python/pair_sieve_cli.py \
  --csv docs/stranger/california_housing_two_col.csv \
  --x-col median_income --y-col median_house_value \
  --x-sense higher --y-sense higher \
  --json --out docs/stranger/
```

### Report (re-run on the exact committed file)

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

Re-run with `--chi` yields pick ∈ front and identical identity_sha256 (ranks unchanged). Default χ remains off.

## Acceptance checklist

| ID | Pass |
|----|------|
| S1 | SOURCE.md names non-authored origin (1990 Census / Pace & Barry / Torgo / StatLib) |
| S2 | CLI run on the committed CSV: identity_ok=true, identity_mode=fenwick_oracle, strategy=Fenwick2D; n matches file |
| S3 | Receipt on branch; book/listing/latency not used |
| S4 | gyro_rank.hpp / Photonic / Geblomi untouched |
| S5 | No UNIV/DAY language |

**Done. One stranger. Stop.**

No investment or trading claims.
