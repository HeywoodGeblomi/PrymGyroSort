#!/usr/bin/env python3
"""Dad Dashboard — live CSV + Yahoo HTTP refresh + report. Not advice. promote_ready=false."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from rank_csv import load_csv, rank_dataframe

try:
    from fetch_watchlist import fetch_scores, DEFAULT_TICKERS
except Exception:
    fetch_scores = None
    DEFAULT_TICKERS = [
        "SNDK", "LITE", "CAT", "GEV", "MU", "RKLB", "TSLA",
        "NVDA", "ETN", "ZS", "BE", "DELL", "MRVL",
    ]

ROOT = Path(__file__).resolve().parents[2]
WATCHLIST = ROOT / "data" / "dad_watchlist.csv"
LIVE = ROOT / "data" / "dad_watchlist_live.csv"
TEMPLATE = ROOT / "data" / "dad_template.csv"


def report_html(out, title: str) -> str:
    show = [c for c in ["ticker", "name", "return_score", "risk_score", "rank"] if c in out.columns]
    top = out.nsmallest(5, "rank")
    head = "".join(f"<th>{c}</th>" for c in show)
    rows = "".join(
        "<tr>" + "".join(f"<td>{out.iloc[i][c]}</td>" for c in show) + "</tr>"
        for i in range(len(out))
    )
    top_rows = "".join(
        "<tr>" + "".join(f"<td>{top.iloc[i][c]}</td>" for c in show) + "</tr>"
        for i in range(len(top))
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: Georgia, serif; font-size: 18px; margin: 2rem; color: #111; }}
h1 {{ font-size: 28px; }} h2 {{ font-size: 22px; margin-top: 1.5rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #333; padding: 8px 12px; text-align: left; }}
th {{ background: #eee; }}
.note {{ color: #444; font-size: 14px; margin-top: 2rem; }}
</style></head><body>
<h1>{title}</h1>
<p>Date: {date.today().isoformat()}</p>
<p><strong>Not investment advice.</strong> Structural ranking only.</p>
<h2>Top 5 to review</h2>
<table><thead><tr>{head}</tr></thead><tbody>{top_rows}</tbody></table>
<h2>Full ranking</h2>
<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>
<p class="note">Lower rank is better. promote_ready=false</p>
</body></html>"""


def main():
    st.set_page_config(page_title="Dad Ranking Report", layout="centered")
    st.title("Dad Ranking Report")
    st.caption("Structural ranking only — not investment advice. promote_ready=false")

    st.subheader("1. Load data")
    source = st.radio(
        "Data source",
        ["Dad watchlist (default)", "Upload CSV"],
        index=0,
        horizontal=True,
    )

    if source == "Dad watchlist (default)":
        st.info(
            "**Load scored live CSV** uses the last Yahoo snapshot in the repo. "
            "**Refresh live data** re-fetches via Yahoo chart HTTP (not yfinance)."
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Load scored live CSV", type="primary"):
                path = LIVE if LIVE.is_file() else WATCHLIST
                if path.is_file():
                    st.session_state["df"] = load_csv(path)
                    st.success(f"Loaded {path.name}")
                else:
                    st.error("No live/watchlist CSV found")
        with c2:
            if st.button("Load placeholders"):
                if WATCHLIST.is_file():
                    st.session_state["df"] = load_csv(WATCHLIST)
                else:
                    st.error("dad_watchlist.csv missing")
        with c3:
            if st.button("Refresh live data"):
                if fetch_scores is None:
                    st.error("fetch_watchlist module missing")
                else:
                    with st.spinner("Yahoo chart HTTP (timeout 10s/ticker)..."):
                        live = fetch_scores(list(DEFAULT_TICKERS))
                    live = live.dropna(subset=["return_score", "risk_score"])
                    if len(live) < 2:
                        st.error(
                            "Live fetch got too few rows. "
                            "Use **Load scored live CSV** or run fetch_watchlist.ps1 on Windows."
                        )
                    else:
                        st.session_state["df"] = live[["ticker", "return_score", "risk_score", "name"]]
                        st.success(f"Fetched {len(live)} tickers")
        if "df" in st.session_state:
            st.dataframe(st.session_state["df"], use_container_width=True, hide_index=True)
    else:
        uploaded = st.file_uploader("Choose CSV file", type=["csv"])
        if TEMPLATE.is_file():
            st.download_button(
                "Download example template CSV",
                data=TEMPLATE.read_bytes(),
                file_name="dad_template.csv",
                mime="text/csv",
            )
        if uploaded is not None:
            try:
                st.session_state["df"] = load_csv(uploaded)
            except Exception as e:
                st.error(str(e))
        if "df" in st.session_state:
            st.dataframe(st.session_state["df"], use_container_width=True, hide_index=True)

    st.subheader("2. Run report")
    if st.button("Run Report", type="primary", use_container_width=True):
        df = st.session_state.get("df")
        if df is None:
            st.error("Load data first.")
        else:
            try:
                st.session_state["out"] = rank_dataframe(df)
            except Exception as e:
                st.error(f"Could not run report: {e}")

    out = st.session_state.get("out")
    if out is not None:
        show = [c for c in ["ticker", "name", "return_score", "risk_score", "rank"] if c in out.columns]
        top = out.nsmallest(5, "rank")
        bottom = out.nlargest(5, "rank")
        st.subheader("Top 5 to review")
        st.dataframe(top[show], use_container_width=True, hide_index=True)
        st.subheader("Bottom 5")
        st.dataframe(bottom[show], use_container_width=True, hide_index=True)
        st.subheader("Full ranking")
        st.dataframe(out[show], use_container_width=True, hide_index=True)
        st.info("Lower rank is better. Not a buy/sell recommendation.")
        st.subheader("3. Download for email")
        st.download_button(
            "Download report CSV",
            data=out[show].to_csv(index=False).encode("utf-8"),
            file_name=f"dad_report_{date.today().isoformat()}.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download report HTML",
            data=report_html(out, "Dad Ranking Report").encode("utf-8"),
            file_name=f"dad_report_{date.today().isoformat()}.html",
            mime="text/html",
        )


if __name__ == "__main__":
    main()
