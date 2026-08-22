# SOURCE.md — Stranger CSV for PGS-STR-001

## Origin (non-authored)

- **Dataset**: California Housing (1990 US Census block groups)
- **URL**: https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/housing/housing.csv
- **Retrieval date**: 2026-08-21
- **Primary origin**: Pace, R. Kelley and Ronald Barry (1997), "Sparse Spatial Autoregressions", Statistics and Probability Letters. Built from 1990 California census data. Obtained via Luís Torgo / StatLib (now closed). Public domain US Census data.
- **License**: Public domain (US Census origin). The handson-ml mirror is commonly used in open ML tutorials; no restrictive terms beyond attribution of origin.
- **We did not author the rows.** This is a classic third-party public dataset.

## Column map

| Column in CSV | Sense | Role |
|---------------|-------|------|
| median_income | higher | x-score (median household income in block group, units of $10k) |
| median_house_value | higher | y-score (median house value in block group, USD) |

Exactly two score columns used. All other original columns ignored.

## How to obtain the ≥10k file (authoritative)

```bash
python3 docs/stranger/filter_california_housing.py
# → docs/stranger/california_housing_two_col.csv  (N=10000 data rows)
```

The script:
1. Downloads the public URL above.
2. Selects only `median_income` and `median_house_value`.
3. Drops non-finite / NA (0 rows dropped; full N=20640).
4. Writes the documented first-10000-row slice (N ≥ 10⁴).

Full 20640 is available by editing `N_SLICE` or removing `.head()`. Receipt was measured on the N=10000 slice produced by this script.

## Notes

- No investment, trading, or financial-product claims.
- Used solely as a product-use stranger input for pair_sieve identity + receipt.
- Slice vs full is explicit per ticket §3.
