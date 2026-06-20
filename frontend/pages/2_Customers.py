# pages/2_Customers.py  —  Customer search and table

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from utils.helpers import (
    load_css, render_sidebar,
    RAW_CUSTOMERS, RISK_COLORS, SEG_COLORS, DRIVER_LABELS,
)

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ChurnWatch — Customers",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
render_sidebar()

# ── Page header ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="cw-page-header">
        <p class="cw-page-title">Customers</p>
        <p class="cw-page-subtitle">12 active accounts · 15 Jun 2026</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Filters ────────────────────────────────────────────────────────────────────

st.markdown('<p class="cw-section-label">Search and Filter</p>', unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns([3, 1.5, 1.5, 1.5])

with f1:
    search = st.text_input(
        "Search",
        placeholder="Search by name, province, segment or card type…",
        label_visibility="collapsed",
    )

with f2:
    risk_filter = st.selectbox(
        "Risk Band",
        options=["All Risk Bands", "Critical", "High", "Medium", "Low"],
        label_visibility="collapsed",
    )

with f3:
    seg_filter = st.selectbox(
        "Segment",
        options=["All Segments", "Affluent", "Mid", "Mass"],
        label_visibility="collapsed",
    )

with f4:
    sort_by = st.selectbox(
        "Sort",
        options=["Highest Risk First", "Lowest Risk First", "Name A–Z", "Salary High–Low"],
        label_visibility="collapsed",
    )

# ── Filter logic ───────────────────────────────────────────────────────────────

filtered = list(RAW_CUSTOMERS)

if search:
    q = search.lower()
    filtered = [
        c for c in filtered
        if q in c["name"].lower()
        or q in c["geography"].lower()
        or q in c["segment"].lower()
        or q in c["card_type"].lower()
    ]

if risk_filter != "All Risk Bands":
    filtered = [c for c in filtered if c["risk_band"] == risk_filter]

if seg_filter != "All Segments":
    filtered = [c for c in filtered if c["segment"] == seg_filter]

sort_map = {
    "Highest Risk First":  lambda c: -c["churn_probability"],
    "Lowest Risk First":   lambda c:  c["churn_probability"],
    "Name A–Z":            lambda c:  c["name"],
    "Salary High–Low":     lambda c: -c["salary"],
}
filtered.sort(key=sort_map[sort_by])

# ── Stats row ──────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)

s1, s2, s3, s4 = st.columns(4)
total     = len(filtered)
critical  = sum(1 for c in filtered if c["risk_band"] == "Critical")
high_risk = sum(1 for c in filtered if c["risk_band"] in ("Critical", "High"))
avg_score = round(
    sum(c["churn_probability"] for c in filtered) / total * 100
) if total else 0

s1.metric("Showing",         total)
s2.metric("Critical Risk",   critical)
s3.metric("Will Leave",      high_risk)
s4.metric("Avg Score",       f"{avg_score}%")

st.markdown("<br>", unsafe_allow_html=True)

# ── Customer cards ─────────────────────────────────────────────────────────────

st.markdown('<p class="cw-section-label">Customer List</p>', unsafe_allow_html=True)

if not filtered:
    st.markdown(
        '<div class="cw-card" style="text-align:center;padding:40px;color:#a0a1b0;">'
        "No customers match your search."
        "</div>",
        unsafe_allow_html=True,
    )
else:
    for i in range(0, len(filtered), 2):
        row_customers = filtered[i:i + 2]
        cols = st.columns(2)

        for col, c in zip(cols, row_customers):
            rc   = RISK_COLORS[c["risk_band"]]
            sc   = SEG_COLORS[c["segment"]]
            pct  = round(c["churn_probability"] * 100)
            prog = c["churn_probability"] * 100

            lc_styles = {
                "At-Risk":  ("rgba(192,104,88,0.1)", "#b85a48"),
                "New":      ("rgba(106,143,203,0.1)", "#5a7abf"),
                "Growing":  ("rgba(90,164,100,0.1)",  "#4a8a5a"),
                "Churned":  ("rgba(160,161,176,0.1)", "#808090"),
            }
            lc_bg, lc_c = lc_styles.get(c["lifecycle"], ("rgba(160,161,176,0.1)", "#808090"))

            driver_label = DRIVER_LABELS.get(c["top_driver"], c["top_driver"])
            sat_color    = "#c06858" if c["satisfaction_score"] <= 2 else "#1e1f2e"
            bal_color    = "#c06858" if c["balance"] == 0 else "#1e1f2e"

            with col:
                st.markdown(
                    f"""
                    <div class="cw-card" style="margin-bottom:12px;">
                        <!-- Header -->
                        <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:12px;">
                            <div style="width:36px;height:36px;border-radius:50%;background:{rc['av_bg']};
                                        display:flex;align-items:center;justify-content:center;
                                        font-size:11px;font-weight:700;color:{rc['color']};flex-shrink:0;">
                                {c['initials']}
                            </div>
                            <div style="flex:1;min-width:0;">
                                <p style="font-size:13px;font-weight:500;color:#1e1f2e;margin:0 0 2px;">{c['name']}</p>
                                <p style="font-size:11px;color:#a0a1b0;margin:0;">
                                    {c['geography']} · {c['card_type']} · {c['gender']}, {c['age']}
                                </p>
                            </div>
                            <span style="font-size:10px;padding:3px 9px;border-radius:20px;font-weight:500;
                                         background:{rc['bg']};color:{rc['color']};white-space:nowrap;">
                                {c['risk_band']}
                            </span>
                        </div>
                        <!-- Badges -->
                        <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px;">
                            <span style="font-size:10px;padding:2px 7px;border-radius:4px;
                                         background:{sc['bg']};color:{sc['color']};">{c['segment']}</span>
                            <span style="font-size:10px;padding:2px 7px;border-radius:4px;
                                         background:{lc_bg};color:{lc_c};">{c['lifecycle']}</span>
                            <span style="font-size:10px;padding:2px 7px;border-radius:4px;
                                         background:#f5f6fa;color:#a0a1b0;">{c['tenure_months']}mo tenure</span>
                            <span style="font-size:10px;padding:2px 7px;border-radius:4px;
                                         background:#f5f6fa;color:#a0a1b0;">R{c['salary']//1000}k salary</span>
                        </div>
                        <!-- Probability bar -->
                        <div style="display:flex;justify-content:space-between;font-size:11px;
                                    color:#a0a1b0;margin-bottom:4px;">
                            <span>Churn probability</span>
                            <span style="font-weight:500;color:{rc['color']};">{pct}%</span>
                        </div>
                        <div class="cw-progress-track">
                            <div class="cw-progress-fill" style="width:{prog}%;background:{rc['color']};"></div>
                        </div>
                        <!-- Driver -->
                        <p style="font-size:11px;color:#a0a1b0;margin:8px 0 10px;">
                            Top driver: {driver_label}
                        </p>
                        <!-- Mini stats -->
                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;
                                    padding-top:10px;border-top:1px solid #f0f1f8;">
                            <div style="text-align:center;">
                                <p style="font-size:12px;font-weight:400;color:{bal_color};margin:0;">
                                    {'R0' if c['balance']==0 else f"R{c['balance']//1000}k"}
                                </p>
                                <p style="font-size:9px;color:#c0c1d0;margin:2px 0 0;text-transform:uppercase;
                                           letter-spacing:.06em;">Balance</p>
                            </div>
                            <div style="text-align:center;">
                                <p style="font-size:12px;font-weight:400;color:#1e1f2e;margin:0;">{c['num_products']}</p>
                                <p style="font-size:9px;color:#c0c1d0;margin:2px 0 0;text-transform:uppercase;
                                           letter-spacing:.06em;">Products</p>
                            </div>
                            <div style="text-align:center;">
                                <p style="font-size:12px;font-weight:400;color:{sat_color};margin:0;">
                                    {c['satisfaction_score']}/5
                                </p>
                                <p style="font-size:9px;color:#c0c1d0;margin:2px 0 0;text-transform:uppercase;
                                           letter-spacing:.06em;">Satisfaction</p>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ── Footer count ───────────────────────────────────────────────────────────────

st.markdown(
    f"<p style='font-size:11px;color:#c0c1d0;text-align:center;margin-top:8px;'>"
    f"Showing {len(filtered)} of {len(RAW_CUSTOMERS)} customers</p>",
    unsafe_allow_html=True,
)
