#!/usr/bin/env python3
"""Dad Dashboard Phase 2 — watchlist, live fetch, emailable report. Not advice. promote_ready=false."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from rank_csv import load_csv, rank_dataframe

try:
    from fetch_watchlist import fetch_scores, DEFAULT_TICKERS
except Exception:
    fetch_scores = None
    DEFAULT_TICKERS = []

ROOT = Path(__file__).resolve().parents[2]
WATCHLIST = ROOT / "data" / "dad_watchlist.csv"
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
<p><strong>Not investment advice.</strong> Structural ranking only. You decide any trades in your brokerage.</p>
<h2>Top 5 to review</h2>
<table><thead><tr>{head}</tr></thead><tbody>{top_rows}</tbody></table>
<h2>Full ranking</h2>
<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>
<p class="note">Lower rank is better (1 = non-dominated). promote_ready=false</p>
</body></html>"""


def main():
    st.set_page_config(page_title="Dad Ranking Report", layout="centered")
    st.markdown(
        """<style>html, body, [class*=\"css\"]  {{ font-size: 1.15rem; }}</style>""",
        unsafe_allow_html=True,
    )
    st.title("Dad Ranking Report")
    st.caption(
        "Structural ranking only — not investment advice. "
        "Manual review for personal use. promote_ready=false"
    )

    st.subheader("1. Load data")
    source = st.radio(
        "Data source",
        ["Dad watchlist (default)", "Upload CSV"],
        index=0,
        horizontal=True,
    )

    if source == "Dad watchlist (default)":
        if WATCHLIST.is_file():
            st.info(
                "Use **Refresh live data** for Yahoo scores, or load CSV placeholders. "
                "Not investment advice."
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Load dad watchlist", type="secondary"):
                    st.session_state["df"] = load_csv(WATCHLIST)
            with c2:
                if st.button("Refresh live data (yfinance)", type="secondary"):
                    if fetch_scores is None:
                        st.error("Install yfinance: py -m pip install yfinance")
                    else:
                        with st.spinner("Fetching Yahoo Finance data..."):
                            live = fetch_scores(list(DEFAULT_TICKERS))
                        live = live.dropna(subset=["return_score", "risk_score"])
                        if len(live) < 2:
                            st.error("Live fetch returned too few rows — try again later")
                        else:
                            st.session_state["df"] = live[["ticker", "return_score", "risk_score", "name"]]
                            st.success(f"Loaded {len(live)} tickers from live data")
            if "df" in st.session_state:
                st.dataframe(st.session_state["df"], use_container_width=True, hide_index=True)
        else:
            st.error("dad_watchlist.csv not found")
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
            st.error("Load the watchlist or upload a CSV first.")
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
        st.subheader("Bottom 5 (higher rank = more dominated)")
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
            "Download report HTML (open → Print → Save as PDF)",
            data=report_html(out, "Dad Ranking Report").encode("utf-8"),
            file_name=f"dad_report_{date.today().isoformat()}.html",
            mime="text/html",
        )


if __name__ == "__main__":
    main()
