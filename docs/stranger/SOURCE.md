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

## Committed file

`california_housing_two_col.csv` in this directory is a **40-row sample**, not the 10,000-row slice. At `c76dee0` the sample measures:

```
n              = 40
front_size     = 1
identity_sha256 = ca9236b163c867ceeb98b0488fcc26a47369aeed8af92c834f7653dbec199315
```

Senses: `median_income` higher, `median_house_value` higher.

## Rebuild the 10,000-row dataset

Do not overwrite the sample. `filter_california_housing.py` writes onto the sample path. The steps below write `/tmp/housing_10k.csv` instead.

Source URL: `https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/housing/housing.csv`

Columns kept: `median_income`, `median_house_value`. Every other column is ignored.

Row selection: drop a row only when either kept value is missing or non-finite (0 rows dropped; 20640 remain), then keep the first 10000 rows in source order.

Censoring: the published file already top-codes `median_house_value` at 500001 and `median_income` at 15.0001. This rebuild keeps those capped rows. It does not drop them and it does not uncap them.

```bash
python3 - << 'PY'
import csv, urllib.request
from pathlib import Path
url = "https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/housing/housing.csv"
text = urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
rows = list(csv.DictReader(text.splitlines()))
clean = []
for r in rows:
    try:
        a = float(r["median_income"]); b = float(r["median_house_value"])
    except (KeyError, TypeError, ValueError):
        continue
    if a == a and b == b:
        clean.append((r["median_income"], r["median_house_value"]))
if len(clean) != 20640:
    raise SystemExit(f"expected 20640 finite rows, got {len(clean)}")
out = Path("/tmp/housing_10k.csv")
with out.open("w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["median_income", "median_house_value"])
    for a, b in clean[:10000]:
        w.writerow([a, b])
print(f"wrote {out} data rows=10000")
PY

python3 python/pair_sieve_cli.py \
  --csv /tmp/housing_10k.csv \
  --x-col median_income --y-col median_house_value \
  --x-sense higher --y-sense higher \
  --bundle /tmp/housing_10k_bundle
```

At `c76dee0` (after the `(x, y)` Fenwick flush) that file measures `n=10000`, `front_size=31`, identity `22cc811f06d78cf00792d4ccf941e96a09cd62b26170d9e58a93bcbc722fa67a`. Before that fix the same file measured identity `3a94ab3104a0f77f7378639f08b816ca7f76b9b00bde432542c7afd682bdb417` and `front_size=32`. The 10,000-row file is not committed.

## Notes

- No investment, trading, or financial-product claims.
- Used solely as a product-use stranger input for pair_sieve identity + receipt.
- Slice vs full is explicit per ticket §3.
