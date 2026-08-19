#!/usr/bin/env python3
"""Fetch return + risk via Yahoo chart HTTP API (no yfinance). Not advice."""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TICKERS = [
    "CRAK", "LITE", "CAT", "GEV", "MU", "RKLB", "TSLA",
    "NVDA", "ETN", "ZS", "BE", "DELL", "MRVL",
]
HTTP_TIMEOUT = 10


def _closes_from_yahoo(ticker: str):
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?range=6mo&interval=1d&events=div%2Csplits"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PrymGyroSort/0.1; +research)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
    try:
        quote = payload["chart"]["result"][0]["indicators"]["quote"][0]
        closes = quote.get("close") or []
        arr = np.array([c for c in closes if c is not None], dtype=np.float64)
        return arr if arr.size >= 10 else None
    except (KeyError, IndexError, TypeError):
        return None


def _scores_from_closes(closes, lookback_days: int):
    window = closes[-min(lookback_days, len(closes)) :]
    ret = float(window[-1] / window[0] - 1.0)
    daily = np.diff(window) / window[:-1]
    vol = float(np.std(daily) * np.sqrt(252)) if daily.size > 2 else float("nan")
    return ret, vol


def fetch_scores(tickers, lookback_days: int = 63):
    rows = []
    for raw in tickers:
        t = (raw or "").strip().upper()
        if not t:
            continue
        print(f"  fetching {t}...", flush=True)
        closes = _closes_from_yahoo(t)
        if closes is None:
            rows.append({"ticker": t, "return_score": np.nan, "risk_score": np.nan, "name": t, "ok": False})
            print(f"  {t}: FAIL", flush=True)
            continue
        ret, vol = _scores_from_closes(closes, lookback_days)
        ok = bool(np.isfinite(ret) and np.isfinite(vol))
        rows.append({"ticker": t, "return_score": ret, "risk_score": vol, "name": t, "ok": ok})
        print(f"  {t}: ok ret={ret:.4f} vol={vol:.4f}", flush=True)
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    ap.add_argument("--lookback-days", type=int, default=63)
    ap.add_argument("--out", default=str(ROOT / "data" / "dad_watchlist_live.csv"))
    args = ap.parse_args()
    tickers = [x.strip() for x in args.tickers.split(",") if x.strip()]
    print(f"[fetch] {len(tickers)} tickers, timeout={HTTP_TIMEOUT}s each", flush=True)
    df = fetch_scores(tickers, lookback_days=args.lookback_days)
    ok = int(df["ok"].sum()) if len(df) and "ok" in df.columns else 0
    out = df[["ticker", "return_score", "risk_score", "name"]].dropna()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"[fetch] ok={ok}/{len(df)} -> {args.out}", flush=True)
    if len(out):
        print(out.to_string(index=False), flush=True)
    return 0 if ok >= 2 else 2


if __name__ == "__main__":
    raise SystemExit(main())
