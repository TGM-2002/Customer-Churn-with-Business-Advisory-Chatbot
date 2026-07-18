# pages/4_Inbox.py 
# Acts like an email inbox for automated churn reports. Every Monday a new report
# lands here showing which customers entered, stayed in, or left the at-risk bands
# that week. The left side lists reports filtered by Week / Month / Year.
# The right side shows the full detail of whichever report is open.

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st

from utils.helpers import (
    load_css, render_sidebar,
    INBOX_MESSAGES, RISK_COLORS,
)

st.set_page_config(
    page_title="CRS — Inbox",
    page_icon=":material/mail:",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
render_sidebar()

# Header 

st.markdown(
    """
    <div class="cw-page-header">
        <p class="cw-page-title">Inbox</p>
        <p class="cw-page-subtitle">Weekly churn alerts · automatically generated every Monday 07:00</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Session state 

if "open_inbox_id" not in st.session_state:
    st.session_state["open_inbox_id"] = INBOX_MESSAGES[0]["id"]

# Period helpers 
# Two small helper functions that read the week string on each report and pull out
# the month and year. These are used to decide which reports appear in each tab.

def _end_month(m):
    # "09 Jun – 15 Jun 2026" → last month token before the year
    parts = m["week"].split()
    return parts[-2]   # e.g. "Jun"

def _year(m):
    return m["week"][-4:]  # e.g. "2026"

_latest_month = _end_month(INBOX_MESSAGES[0])
_latest_year  = _year(INBOX_MESSAGES[0])

PERIOD_MSGS = {
    "Week":  INBOX_MESSAGES[:1],
    "Month": [m for m in INBOX_MESSAGES if _end_month(m) == _latest_month],
    "Year":  [m for m in INBOX_MESSAGES if _year(m) == _latest_year],
}

# Layout 

list_col, msg_col = st.columns([1.1, 2.9], gap="large")

# Left: period tabs + message list
# _render_msg_list draws the report list for a given set of messages.
# Each report shows the subject, date, and Critical/High badges.
# Clicking "Open" sets the selected report ID in session state and refreshes the page
# so the right column updates to show that report's details.
# The prefix argument makes each button key unique so the same report can appear
# in multiple tabs without causing a duplicate widget error.

def _render_msg_list(messages, prefix):
    if not messages:
        st.markdown('<p style="font-size:12px;color:#9992b0;padding:8px 0;">No reports in this period.</p>',
                    unsafe_allow_html=True)
        return
    for msg in messages:
        is_open = msg["id"] == st.session_state["open_inbox_id"]
        dot_cls = "inbox-dot" if msg["unread"] else "inbox-dot read"
        row_cls = "inbox-row active" if is_open else "inbox-row"

        crit_badge = (
            f'<span class="inbox-badge" style="background:#fef2f2;color:#dc2626;">'
            f'{msg["critical_count"]} Critical</span>'
        ) if msg["critical_count"] > 0 else ""
        high_badge = (
            f'<span class="inbox-badge" style="background:#fff7ed;color:#ea580c;">'
            f'{msg["high_count"]} High</span>'
        ) if msg["high_count"] > 0 else ""

        st.markdown(
            f"""
            <div class="{row_cls}">
                <div class="{dot_cls}" style="margin-top:6px;flex-shrink:0;"></div>
                <div style="flex:1;min-width:0;">
                    <p class="inbox-subject">{msg['subject'][:50]}{'…' if len(msg['subject'])>50 else ''}</p>
                    <p class="inbox-meta">{msg['sent']} · {msg['week']}</p>
                    <div style="display:flex;gap:4px;margin-top:6px;flex-wrap:wrap;">
                        {crit_badge}{high_badge}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open", key=f"{prefix}_{msg['id']}", use_container_width=True,
                     help=msg["subject"]):
            st.session_state["open_inbox_id"] = msg["id"]
            st.rerun()

with list_col:
    tab_week, tab_month, tab_year = st.tabs(["Week", "Month", "Year"])
    with tab_week:
        st.markdown(f'<p class="cw-section-label">This week · {len(PERIOD_MSGS["Week"])} report(s)</p>',
                    unsafe_allow_html=True)
        _render_msg_list(PERIOD_MSGS["Week"], "w")
    with tab_month:
        st.markdown(f'<p class="cw-section-label">{_latest_month} {_latest_year} · {len(PERIOD_MSGS["Month"])} report(s)</p>',
                    unsafe_allow_html=True)
        _render_msg_list(PERIOD_MSGS["Month"], "m")
    with tab_year:
        st.markdown(f'<p class="cw-section-label">{_latest_year} · {len(PERIOD_MSGS["Year"])} report(s)</p>',
                    unsafe_allow_html=True)
        _render_msg_list(PERIOD_MSGS["Year"], "y")

# Right: open message
# Shows the full detail of whichever report is currently open.
# Starts with a header card (subject, date, four stat tiles), then an action
# banner saying what needs to happen urgently, then collapsible sections for
# customers grouped by risk band, then a plain-English weekly summary,
# and finally two buttons to jump to the Customers or AI Advisory pages.

with msg_col:
    msg = next(
        (m for m in INBOX_MESSAGES if m["id"] == st.session_state["open_inbox_id"]),
        INBOX_MESSAGES[0],
    )

    # Message header 

    st.markdown(
        f"""
        <div style="background:#ffffff;border:1px solid #e8e3f2;border-radius:12px;
                     padding:18px 22px;margin-bottom:14px;">
            <p style="font-size:15px;font-weight:600;color:#1a1826;margin:0 0 3px;">
                {msg['subject']}
            </p>
            <p style="font-size:11px;color:#9992b0;margin:0 0 14px;">
                Sent {msg['sent']} · Week of {msg['week']}
            </p>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
                <div style="background:#fef2f2;border-radius:8px;padding:12px;text-align:center;">
                    <p style="font-size:22px;font-weight:300;color:#dc2626;margin:0 0 2px;">{msg['critical_count']}</p>
                    <p style="font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:#9992b0;margin:0;">Critical</p>
                </div>
                <div style="background:#fff7ed;border-radius:8px;padding:12px;text-align:center;">
                    <p style="font-size:22px;font-weight:300;color:#ea580c;margin:0 0 2px;">{msg['high_count']}</p>
                    <p style="font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:#9992b0;margin:0;">High Risk</p>
                </div>
                <div style="background:#fef9c3;border-radius:8px;padding:12px;text-align:center;">
                    <p style="font-size:22px;font-weight:300;color:#a16207;margin:0 0 2px;">{msg['new_entries']}</p>
                    <p style="font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:#9992b0;margin:0;">New at-risk</p>
                </div>
                <div style="background:#f0fdf4;border-radius:8px;padding:12px;text-align:center;">
                    <p style="font-size:22px;font-weight:300;color:#16a34a;margin:0 0 2px;">{msg['improvement']}</p>
                    <p style="font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:#9992b0;margin:0;">Improved</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action required banner 

    st.markdown(
        f"""
        <div style="background:#f5f3ff;border:1px solid rgba(124,58,237,0.25);
                     border-radius:10px;padding:12px 16px;margin-bottom:16px;
                     display:flex;gap:10px;align-items:flex-start;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                 stroke="#7c3aed" stroke-width="2" stroke-linecap="round" style="flex-shrink:0;margin-top:1px;">
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <p style="font-size:12px;color:#5b21b6;margin:0;line-height:1.6;">
                <strong>Action required:</strong> {msg['action']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    #Categorised customer sections 

    st.markdown('<p class="cw-section-label">Customers by Risk Category</p>', unsafe_allow_html=True)

    # Derive categories from top_customers
    by_risk = {"Critical": [], "High": [], "Medium": [], "Low": []}
    for cust in msg["top_customers"]:
        band = cust.get("risk", "Low")
        if band in by_risk:
            by_risk[band].append(cust)

    CAT_META = {
        "Critical": {"color": "#dc2626", "bg": "#fef2f2", "label": "Critical Risk", "expanded": False},
        "High":     {"color": "#ea580c", "bg": "#fff7ed", "label": "High Risk",     "expanded": False},
        "Medium":   {"color": "#d97706", "bg": "#fffbeb", "label": "Medium Risk",   "expanded": False},
        "Low":      {"color": "#16a34a", "bg": "#f0fdf4", "label": "Low Risk",      "expanded": False},
    }

    for band, meta in CAT_META.items():
        customers = by_risk[band]
        if not customers:
            continue

        rc = RISK_COLORS[band]
        with st.expander(
            f"{meta['label']} — {len(customers)} customer{'s' if len(customers)!=1 else ''}",
            expanded=meta["expanded"],
        ):
            for cust in customers:
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:12px;
                                 padding:12px 16px;background:#ffffff;border:1px solid #e8e3f2;
                                 border-radius:10px;margin-bottom:6px;">
                        <div style="width:34px;height:34px;border-radius:50%;background:{rc['av_bg']};
                                     display:flex;align-items:center;justify-content:center;
                                     font-size:10px;font-weight:700;color:{rc['color']};flex-shrink:0;">
                            {cust['initials']}
                        </div>
                        <div style="flex:1;min-width:0;">
                            <p style="font-size:13px;font-weight:500;color:#1a1826;margin:0 0 2px;">{cust['name']}</p>
                            <p style="font-size:11px;color:#9992b0;margin:0;">
                                Top driver: {cust['driver']}
                            </p>
                        </div>
                        <div style="text-align:right;flex-shrink:0;">
                            <p style="font-size:20px;font-weight:300;color:{rc['color']};margin:0 0 2px;">
                                {cust['prob']}%
                            </p>
                            <span style="font-size:10px;padding:2px 8px;border-radius:20px;
                                          background:{rc['bg']};color:{rc['color']};font-weight:500;">
                                {cust['risk']}
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # Weekly summary 

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    st.markdown('<p class="cw-section-label">Weekly Summary</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="background:#ffffff;border:1px solid #e8e3f2;border-radius:10px;
                     padding:16px 18px;margin-bottom:16px;">
            <p style="font-size:13px;color:#44403c;line-height:1.80;margin:0;">
                {msg['summary']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Navigation 

    b1, b2 = st.columns(2, gap="medium")
    with b1:
        if st.button("View all customers", use_container_width=True):
            st.switch_page("pages/2_Customers.py")
    with b2:
        if st.button("Open AI Advisory", use_container_width=True):
            st.switch_page("pages/3_AI_Advisory.py")
