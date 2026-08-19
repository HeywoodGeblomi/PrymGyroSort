#!/usr/bin/env python3
"""Fetch return + risk proxies via yfinance for dad watchlist. Not advice. promote_ready=false."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TICKERS = [
    "SNDK", "LITE", "CAT", "GEV", "MU", "RKLB", "TSLA",
    "NVDA", "ETN", "ZS", "BE", "DELL", "MRVL",
]


def fetch_scores(tickers: list[str], lookback_days: int = 63) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as e:
        raise SystemExit("Install yfinance: py -m pip install yfinance") from e

    rows = []
    for t in tickers:
        t = t.strip().upper()
        if not t:
            continue
        try:
            hist = yf.Ticker(t).history(period="6mo")
            if hist is None or hist.empty or "Close" not in hist.columns:
                rows.append({"ticker": t, "return_score": np.nan, "risk_score": np.nan, "name": t, "ok": False})
                continue
            close = hist["Close"].dropna()
            if len(close) < 10:
                rows.append({"ticker": t, "return_score": np.nan, "risk_score": np.nan, "name": t, "ok": False})
                continue
            window = close.iloc[-min(lookback_days, len(close)) :]
            ret = float(window.iloc[-1] / window.iloc[0] - 1.0)
            daily = window.pct_change().dropna()
            vol = float(daily.std() * np.sqrt(252)) if len(daily) > 2 else np.nan
            info_name = t
            try:
                info = yf.Ticker(t).info or {}
                info_name = info.get("shortName") or info.get("longName") or t
            except Exception:
                pass
            rows.append({
                "ticker": t,
                "return_score": ret,
                "risk_score": vol,
                "name": info_name,
                "ok": bool(np.isfinite(ret) and np.isfinite(vol)),
            })
        except Exception:
            rows.append({"ticker": t, "return_score": np.nan, "risk_score": np.nan, "name": t, "ok": False})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    ap.add_argument("--lookback-days", type=int, default=63)
    ap.add_argument("--out", default=str(ROOT / "data" / "dad_watchlist_live.csv"))
    args = ap.parse_args()
    tickers = [x.strip() for x in args.tickers.split(",") if x.strip()]
    df = fetch_scores(tickers, lookback_days=args.lookback_days)
    ok = int(df["ok"].sum()) if "ok" in df.columns else 0
    out = df[["ticker", "return_score", "risk_score", "name"]].dropna()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"[fetch] ok={ok}/{len(df)} → {args.out}")
    print(out.to_string(index=False))
    return 0 if ok >= 2 else 2


if __name__ == "__main__":
    raise SystemExit(main())
