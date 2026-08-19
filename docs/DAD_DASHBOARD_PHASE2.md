# Dad Dashboard — Phase 2 (live fetch + cloud access)

**promote_ready=false** — not investment advice.

## 1. Live scores (yfinance)

```bash
py -m pip install yfinance
py python/dad_app/fetch_watchlist.py
```

Writes `data/dad_watchlist_live.csv`.

In the Streamlit UI: **Refresh live data (yfinance)**.

| Field | Definition |
|-------|------------|
| return_score | ~3-month trailing total return |
| risk_score | Annualized realized volatility of daily returns |

Yahoo data is free, unofficial, and can fail or lag. Treat as a convenience, not a data vendor.

## 2. Easiest private-ish URL: Streamlit Community Cloud

1. Repo is on GitHub: `HeywoodGeblomi/PrymGyroSort`
2. Go to https://share.streamlit.io and sign in with GitHub
3. **New app** → repo → branch `main` → Main file path: `python/dad_app/app.py`
4. Advanced → Requirements file: `requirements-dad.txt`
5. Deploy → URL like `https://xxx.streamlit.app`
6. Email that URL only to your dad (unlisted link). Optional: restrict access in Streamlit Cloud settings if available.

### Limits

- Free tier sleeps when idle; first load is slow
- Not bank-grade private hosting
- yfinance may rate-limit cloud IPs
- Still not investment advice — banner stays on

## 3. Dad workflow

1. Open the URL
2. **Refresh live data (yfinance)**
3. **Run Report**
4. Read Top 5 / full ranking
