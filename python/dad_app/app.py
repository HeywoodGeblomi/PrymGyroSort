#!/usr/bin/env python3
"""Dad Dashboard — Phase 0 Streamlit UI. Not investment advice. promote_ready=false."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from rank_csv import load_csv, rank_dataframe

ROOT = Path(__file__).resolve().parents[2]


def main():
    st.set_page_config(page_title="Ranking Report", layout="centered")
    st.markdown(
        """
        <style>
        html, body, [class*="css"]  { font-size: 1.15rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Ranking Report")
    st.caption(
        "Structural ranking only — not investment advice. "
        "You decide trades in your own brokerage. promote_ready=false"
    )

    st.subheader("1. Upload CSV")
    st.markdown(
        "Required columns: **`ticker`**, **`return_score`** (higher better), "
        "**`risk_score`** (higher = more risk)."
    )
    uploaded = st.file_uploader("Choose CSV file", type=["csv"])

    template = ROOT / "data" / "dad_template.csv"
    if template.is_file():
        st.download_button(
            "Download template CSV",
            data=template.read_bytes(),
            file_name="dad_template.csv",
            mime="text/csv",
        )

    if st.button("Run Report", type="primary", use_container_width=True):
        if uploaded is None:
            st.error("Please upload a CSV first.")
            return
        try:
            df = load_csv(uploaded)
            out = rank_dataframe(df)
            top = out.nsmallest(5, "rank")
            bottom = out.nlargest(5, "rank")
            show = [c for c in ["ticker", "name", "return_score", "risk_score", "rank"] if c in out.columns]

            st.subheader("Top 5 to review")
            st.dataframe(top[show], use_container_width=True, hide_index=True)
            st.subheader("Bottom 5 (higher rank = more dominated)")
            st.dataframe(bottom[show], use_container_width=True, hide_index=True)
            st.subheader("Full ranking")
            st.dataframe(out[show], use_container_width=True, hide_index=True)
            st.info(
                "Lower rank is better (rank 1 = non-dominated). "
                "This is not a buy/sell recommendation."
            )
        except Exception as e:
            st.error(f"Could not run report: {e}")


if __name__ == "__main__":
    main()
