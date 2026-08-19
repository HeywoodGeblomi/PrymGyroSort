#!/usr/bin/env python3
"""Fetch return + risk proxies via yfinance. No .info(); hard timeouts. Not advice."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TICKERS = [
    "SNDK", "LITE", "CAT", "GEV", "MU", "RKLB", "TSLA",
    "NVDA", "ETN", "ZS", "BE", "DELL", "MRVL",
]
TICKER_TIMEOUT_SEC = 15


def _one_ticker(t: str, lookback_days: int) -> dict:
    import yfinance as yf

    t = t.strip().upper()
    empty = {"ticker": t, "return_score": np.nan, "risk_score": np.nan, "name": t, "ok": False}
    try:
        hist = yf.Ticker(t).history(period="6mo", auto_adjust=True, actions=False)
        if hist is None or hist.empty or "Close" not in hist.columns:
            return empty
        close = hist["Close"].dropna()
        if len(close) < 10:
            return empty
        window = close.iloc[-min(lookback_days, len(close)) :]
        ret = float(window.iloc[-1] / window.iloc[0] - 1.0)
        daily = window.pct_change().dropna()
        vol = float(daily.std() * np.sqrt(252)) if len(daily) > 2 else np.nan
        ok = bool(np.isfinite(ret) and np.isfinite(vol))
        return {"ticker": t, "return_score": ret, "risk_score": vol, "name": t, "ok": ok}
    except Exception:
        return empty


def fetch_scores(tickers: list[str], lookback_days: int = 63) -> pd.DataFrame:
    try:
        import yfinance  # noqa: F401
    except ImportError as e:
        raise RuntimeError("Install yfinance: py -m pip install yfinance") from e

    rows = []
    with ThreadPoolExecutor(max_workers=1) as ex:
        for t in tickers:
            t = (t or "").strip()
            if not t:
                continue
            fut = ex.submit(_one_ticker, t, lookback_days)
            try:
                rows.append(fut.result(timeout=TICKER_TIMEOUT_SEC))
            except (FuturesTimeout, Exception):
                rows.append(
                    {
                        "ticker": t.upper(),
                        "return_score": np.nan,
                        "risk_score": np.nan,
                        "name": t.upper(),
                        "ok": False,
                    }
                )
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    ap.add_argument("--lookback-days", type=int, default=63)
    ap.add_argument("--out", default=str(ROOT / "data" / "dad_watchlist_live.csv"))
    args = ap.parse_args()
    tickers = [x.strip() for x in args.tickers.split(",") if x.strip()]
    df = fetch_scores(tickers, lookback_days=args.lookback_days)
    ok = int(df["ok"].sum()) if len(df) and "ok" in df.columns else 0
    out = df[["ticker", "return_score", "risk_score", "name"]].dropna()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"[fetch] ok={ok}/{len(df)} -> {args.out}")
    print(out.to_string(index=False))
    return 0 if ok >= 2 else 2


if __name__ == "__main__":
    raise SystemExit(main())
