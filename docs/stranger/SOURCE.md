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

## Row filter + documented slice

1. Load full CSV from the URL above (N_raw = 20 640).
2. Select only `median_income` and `median_house_value`.
3. Drop any row where either value is non-numeric or non-finite. Both columns are complete → 0 dropped. Full N = 20 640.
4. **Documented slice checked in**: first 10 000 rows after the filter (N = 10 000 ≥ 10⁴). The committed file `docs/stranger/california_housing_two_col.csv` contains exactly these 10 000 rows. Full data is recoverable from the public URL + the filter script below.

Filter + slice script (reproducible):

```python
import pandas as pd
df = pd.read_csv("https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/housing/housing.csv")
clean = df[["median_income", "median_house_value"]].dropna()
assert clean.shape[0] == 20640
slice10k = clean.head(10000)
slice10k.to_csv("california_housing_two_col.csv", index=False)
# wc -l california_housing_two_col.csv  → 10001 (header + 10000)
```

## Notes

- No investment, trading, or financial-product claims.
- Used solely as a product-use stranger input for pair_sieve identity + receipt.
- Slice vs full is explicit per ticket §3. Receipt n matches the committed file.
