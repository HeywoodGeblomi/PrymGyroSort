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

Exactly two score columns used. All other original columns (longitude, latitude, housing_median_age, total_rooms, total_bedrooms, population, households, ocean_proximity) ignored.

## Row filter

1. Load full CSV (N_raw = 20 640).
2. Select only `median_income` and `median_house_value`.
3. Drop any row where either value is non-numeric or non-finite (NaN/Inf). In this mirror both columns are complete: **0 rows dropped**.
4. Resulting N = **20 640**. Full dataset (not a slice).

Filter script (reproducible):

```python
import pandas as pd
df = pd.read_csv("housing.csv")
clean = df[["median_income", "median_house_value"]].dropna()
assert clean.shape[0] == 20640
clean.to_csv("california_housing_two_col.csv", index=False)
```

## Notes

- No investment, trading, or financial-product claims.
- Used solely as a product-use stranger input for pair_sieve identity + receipt.
