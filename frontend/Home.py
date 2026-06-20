# Home.py  —  ChurnWatch landing page

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import streamlit as st
from utils.helpers import load_css, render_sidebar

st.set_page_config(
    page_title="ChurnWatch",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
render_sidebar()

# ── Hero ───────────────────────────────────────────────────────────────────────

_, mid, _ = st.columns([1, 2, 1])
with mid:
    st.markdown(
        """
        <div style="text-align:center;padding:48px 0 32px;">
            <div style="width:56px;height:56px;border-radius:16px;
                         background:rgba(77,138,126,0.1);border:1px solid rgba(77,138,126,0.22);
                         display:flex;align-items:center;justify-content:center;
                         font-size:24px;margin:0 auto 20px;">📊</div>
            <h1 style="font-size:32px!important;font-weight:300!important;
                        color:#1e1f2e!important;letter-spacing:0.04em;margin:0 0 8px;">
                ChurnWatch
            </h1>
            <p style="font-size:14px;color:#8a8b9a;letter-spacing:0.06em;
                       text-transform:uppercase;margin:0 0 32px;">
                Customer Churn Advisory System
            </p>
            <div style="border-top:1px solid #e8e9f2;margin-bottom:32px;"></div>
            <p style="font-size:13px;color:#6b6c80;line-height:1.7;margin:0 0 40px;">
                Predict customer churn, visualise risk segments with Self-Organizing Maps,
                and generate AI-powered retention strategies for your retail banking portfolio.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Navigation cards ───────────────────────────────────────────────────────

    c1, c2, c3 = st.columns(3)

    for col, icon, label, desc, page, color in [
        (c1, "📈", "Dashboard",   "KPIs, SOM visualisations,\nand churn analytics",       "pages/1_Dashboard.py",   "#4d8a7e"),
        (c2, "👤", "Customers",   "Search, filter, and view\nindividual customer risk",   "pages/2_Customers.py",   "#6a8fcb"),
        (c3, "🤖", "AI Advisory", "Why customers churn\nand how to retain them",         "pages/3_AI_Advisory.py", "#b08040"),
    ]:
        with col:
            st.markdown(
                f"""
                <div style="background:#ffffff;border:1px solid #e4e5f0;border-radius:12px;
                             padding:22px 20px;text-align:center;height:100%;">
                    <div style="font-size:22px;margin-bottom:10px;">{icon}</div>
                    <p style="font-size:13px;font-weight:600;color:#1e1f2e;margin:0 0 6px;">{label}</p>
                    <p style="font-size:11px;color:#a0a1b0;line-height:1.6;margin:0 0 16px;
                               white-space:pre-line;">{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Open {label}", key=f"btn_{label}", use_container_width=True):
                st.switch_page(page)

    # ── Portfolio snapshot ─────────────────────────────────────────────────────

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:10px;text-transform:uppercase;letter-spacing:.1em;'
        'color:#b0b1c0;text-align:center;margin-bottom:14px;">Portfolio Snapshot</p>',
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Customers",  "2,847", "+124 this month")
    m2.metric("At Risk",          "436",   "+38 from last month",          delta_color="inverse")
    m3.metric("Churn Rate",       "15.3%", "+0.4pp month-on-month",        delta_color="inverse")
    m4.metric("Revenue at Risk",  "R12.4M", "Critical attention needed",   delta_color="inverse")

    st.markdown(
        '<p style="font-size:10px;color:#c0c1d0;text-align:center;margin-top:24px;">'
        'Last updated 15 Jun 2026 · ChurnWatch v1.0</p>',
        unsafe_allow_html=True,
    )
