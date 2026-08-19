# Dad Dashboard — Phase 0

**Product:** Local ranking report for manual review (retail brokerage).  
**Not:** advice, auto-trading, alpha, or live orders.  
**promote_ready=false**

## Input (locked)

**Format:** UTF-8 CSV only (no API in Phase 0).

| Column | Required | Notes |
|--------|----------|-------|
| ticker | yes | Symbol |
| return_score | yes | Higher better |
| risk_score | yes | Higher = more risk (worse) |
| name | no | Display only |

Template: `data/dad_template.csv`

Mapping to sieve (lower-better M=2):

- obj0 = normalize(−return_score)
- obj1 = normalize(risk_score)

## UI

Streamlit: upload CSV → **Run Report** → Top 5 / Bottom 5 + full ranked table.

## Run (local)

```bash
pip install streamlit pandas
streamlit run python/dad_app/app.py
```

CLI rank without UI:

```bash
python3 python/dad_app/rank_csv.py data/dad_template.csv
```
