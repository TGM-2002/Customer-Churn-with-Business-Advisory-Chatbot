# Home.py Customer Retention System landing page
# This is the first page the user sees. It shows the system name, navigation cards
# to every other page, and a quick portfolio snapshot at the bottom.

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import streamlit as st
from utils.helpers import load_css, render_sidebar, NAV_ICONS

st.set_page_config(
    page_title="Customer Retention System",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
render_sidebar()

# Hero header 
# Shows the system name "Customer Retention System" in large gradient text at the top
# of the page, with the slogan directly underneath it.

st.markdown(
    """
    <div style="text-align:center;padding:48px 0 32px;">
        <h1 style="font-size:42px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;
                    margin:0 0 10px;background:linear-gradient(135deg,#1a1826 0%,#5b21b6 45%,#a855f7 100%);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;">
            Customer Retention System
        </h1>
        <p style="font-size:13px;color:#1a1826;letter-spacing:0.20em;text-transform:uppercase;
                   font-weight:500;margin:0;">
            Retain &nbsp;·&nbsp; Relate &nbsp;·&nbsp; Grow
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Navigation cards 
# Draws four equal-sized cards side by side , one for each main page.
# Each card has an icon, a title, a short description, and an "Open" button that
# takes the user straight to that page when clicked.

st.markdown('<p class="cw-section-label" style="text-align:center;">Navigate</p>',
            unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4, gap="medium")

nav_items = [
    (c1, "dashboard",  "Dashboard",
     "KPIs and churn analytics\nacross your portfolio",          "pages/1_Dashboard.py"),
    (c2, "customers",  "Customers",
     "Search, filter, and review\nindividual customer risk",     "pages/2_Customers.py"),
    (c3, "advisory",   "AI Advisory",
     "Understand why customers churn\nand how to retain them",   "pages/3_AI_Advisory.py"),
    (c4, "inbox",      "Inbox",
     "Weekly automated churn alerts\norganised by risk category","pages/4_Inbox.py"),
]

for col, icon_key, label, desc, page in nav_items:
    with col:
        st.markdown(
            f"""
            <div class="cw-nav-card">
                <div class="cw-nav-card-icon">{NAV_ICONS[icon_key]}</div>
                <p class="cw-nav-card-title">{label}</p>
                <p class="cw-nav-card-desc">{desc}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button(f"Open {label}", key=f"btn_{label}", use_container_width=True):
            st.switch_page(page)

# Portfolio snapshot 
# Shows four key numbers for the whole customer portfolio at a glance 
# total customers, how many are at risk, the overall churn rate, and revenue at risk.

st.markdown("<div style='margin-top:36px;'></div>", unsafe_allow_html=True)
st.markdown(
    '<p class="cw-section-label" style="text-align:center;">Portfolio Snapshot · Jun 2026</p>',
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4, gap="medium")
m1.metric("Total Customers",  "2,847", "+124 this month")
m2.metric("At Risk",          "436",   "+38 from last month",        delta_color="inverse")
m3.metric("Churn Rate",       "15.3%", "+0.4pp month-on-month",      delta_color="inverse")
m4.metric("Revenue at Risk",  "R12.4M", "Critical attention needed", delta_color="inverse")

st.markdown(
    '<p style="font-size:10px;color:#9992b0;text-align:center;margin-top:20px;">'
    'Customer Retention System v1.0 · AI-Powered Churn Intelligence</p>',
    unsafe_allow_html=True,
)
