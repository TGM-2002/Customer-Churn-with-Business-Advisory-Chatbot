# pages/3_AI_Advisory.py  —  AI-powered churn advisory

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st

from utils.helpers import (
    load_css, render_sidebar,
    RAW_CUSTOMERS, RISK_COLORS, SEG_COLORS, DRIVER_LABELS,
    STEP_TAG_STYLES, get_customer_names, get_customer_by_name,
)

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ChurnWatch — AI Advisory",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
render_sidebar()

# ── Page header ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="cw-page-header">
        <p class="cw-page-title">AI Advisory</p>
        <p class="cw-page-subtitle">Powered by ChromaDB and Claude · 15 Jun 2026</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Customer selector ──────────────────────────────────────────────────────────

st.markdown('<p class="cw-section-label">Select Customer</p>', unsafe_allow_html=True)

high_risk = sorted(
    [c for c in RAW_CUSTOMERS if c["risk_band"] in ("Critical", "High")],
    key=lambda c: -c["churn_probability"],
)

sel_col, info_col = st.columns([1, 2])

with sel_col:
    names = [c["name"] for c in high_risk] + [
        c["name"] for c in RAW_CUSTOMERS if c["risk_band"] not in ("Critical", "High")
    ]

    selected_name = st.selectbox(
        "Customer",
        options=names,
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="cw-section-label">Quick Select — Critical and High Risk</p>', unsafe_allow_html=True)

    for c in high_risk[:4]:
        rc  = RISK_COLORS[c["risk_band"]]
        pct = round(c["churn_probability"] * 100)
        is_selected = c["name"] == selected_name
        border = f"2px solid {rc['color']}" if is_selected else "1px solid #e4e5f0"
        bg     = rc["bg"] if is_selected else "#ffffff"

        st.markdown(
            f"""
            <div style="background:{bg};border:{border};border-radius:10px;
                         padding:11px 14px;margin-bottom:8px;cursor:pointer;">
                <p style="font-size:12px;font-weight:500;color:#1e1f2e;margin:0 0 2px;">{c['name']}</p>
                <p style="font-size:10px;color:#a0a1b0;margin:0 0 6px;">
                    {c['segment']} · {c['geography']} · {c['card_type']}
                </p>
                <span style="font-size:16px;font-weight:300;color:{rc['color']};">{pct}%</span>
                <span style="font-size:10px;padding:2px 8px;border-radius:20px;margin-left:6px;
                              background:{rc['bg']};color:{rc['color']};font-weight:500;">
                    {c['risk_band']}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Advisory output ────────────────────────────────────────────────────────────

customer = get_customer_by_name(selected_name)

if not customer:
    st.error("Customer not found.")
    st.stop()

with info_col:
    rc   = RISK_COLORS[customer["risk_band"]]
    sc   = SEG_COLORS[customer["segment"]]
    pct  = round(customer["churn_probability"] * 100)
    prog = customer["churn_probability"] * 100

    lc_styles = {
        "At-Risk":  ("rgba(192,104,88,0.1)", "#b85a48"),
        "New":      ("rgba(106,143,203,0.1)", "#5a7abf"),
        "Growing":  ("rgba(90,164,100,0.1)",  "#4a8a5a"),
        "Churned":  ("rgba(160,161,176,0.1)", "#808090"),
    }
    lc_bg, lc_c = lc_styles.get(customer["lifecycle"], ("rgba(160,161,176,0.1)", "#808090"))

    # ── Customer header card ─────────────────────────────────────────────────

    st.markdown(
        f"""
        <div class="cw-card" style="margin-bottom:14px;">
            <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;
                         padding-bottom:14px;border-bottom:1px solid #f0f1f8;">
                <div style="width:42px;height:42px;border-radius:50%;background:{rc['av_bg']};
                             display:flex;align-items:center;justify-content:center;
                             font-size:13px;font-weight:700;color:{rc['color']};flex-shrink:0;">
                    {customer['initials']}
                </div>
                <div style="flex:1;">
                    <p style="font-size:15px;font-weight:500;color:#1e1f2e;margin:0 0 3px;">{customer['name']}</p>
                    <p style="font-size:11px;color:#a0a1b0;margin:0 0 8px;">
                        {customer['geography']} · {customer['card_type']} ·
                        {customer['gender']}, {customer['age']} · {customer['tenure_months']} months tenure
                    </p>
                    <div style="display:flex;gap:5px;flex-wrap:wrap;">
                        <span style="font-size:10px;padding:2px 7px;border-radius:4px;
                                      background:{sc['bg']};color:{sc['color']};">
                            {customer['segment']}
                        </span>
                        <span style="font-size:10px;padding:2px 7px;border-radius:4px;
                                      background:{lc_bg};color:{lc_c};">
                            {customer['lifecycle']}
                        </span>
                        <span style="font-size:10px;padding:2px 7px;border-radius:4px;
                                      background:#f5f6fa;color:#a0a1b0;">
                            {'Active' if customer['is_active'] else 'Inactive'}
                        </span>
                    </div>
                </div>
                <div style="text-align:right;flex-shrink:0;">
                    <p style="font-size:28px;font-weight:300;color:{rc['color']};
                               line-height:1;margin:0 0 4px;">{pct}%</p>
                    <span style="font-size:10px;padding:3px 10px;border-radius:20px;font-weight:500;
                                  background:{rc['bg']};color:{rc['color']};">
                        {customer['risk_band']} Risk
                    </span>
                </div>
            </div>
            <!-- Stats row -->
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
                <div class="adv-stat-card">
                    <p class="adv-stat-val" style="{'color:#c06858' if customer['balance']==0 else ''};">
                        {'R0' if customer['balance']==0 else f"R{customer['balance']//1000}k"}
                    </p>
                    <p class="adv-stat-lbl">Balance</p>
                </div>
                <div class="adv-stat-card">
                    <p class="adv-stat-val">{customer['num_products']}</p>
                    <p class="adv-stat-lbl">Products</p>
                </div>
                <div class="adv-stat-card">
                    <p class="adv-stat-val" style="{'color:#c06858' if customer['satisfaction_score']<=2 else ''};">
                        {customer['satisfaction_score']}/5
                    </p>
                    <p class="adv-stat-lbl">Satisfaction</p>
                </div>
                <div class="adv-stat-card">
                    <p class="adv-stat-val">{customer['credit_score']}</p>
                    <p class="adv-stat-lbl">Credit Score</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Why churning ──────────────────────────────────────────────────────────

    st.markdown(
        '<p class="cw-section-label">Why This Customer Is at Risk of Churning</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="adv-why-box">{customer["why"]}</div>',
        unsafe_allow_html=True,
    )

    # Risk signal chips
    if customer["flags"]:
        flag_labels = {
            "activity_drop_flag":   ("Inactive member",        "#fef1ef", "#b85a48"),
            "has_zero_balance":     ("Zero account balance",   "#fef5e8", "#b08040"),
            "is_single_product":    ("Single product only",    "#eef2fc", "#5a7abf"),
            "is_high_risk_support": ("Complaint + dissatisfied","#fef1ef", "#b85a48"),
            "low_points":           ("Low loyalty engagement", "#eef2fc", "#5a7abf"),
        }
        chips = ""
        for f in customer["flags"]:
            lbl, bg, col = flag_labels.get(f, (f, "#f5f6fa", "#a0a1b0"))
            chips += (
                f'<span class="adv-flag" style="background:{bg};color:{col};">{lbl}</span>'
            )
        st.markdown(
            f'<div class="adv-flag-wrap">{chips}</div>',
            unsafe_allow_html=True,
        )

    # ── Retention steps ───────────────────────────────────────────────────────

    st.markdown(
        '<p class="cw-section-label">5-Step Retention Action Plan</p>',
        unsafe_allow_html=True,
    )

    done_count = 0
    for i, step in enumerate(customer["steps"], 1):
        ts = STEP_TAG_STYLES.get(step["tag"], STEP_TAG_STYLES["Follow up"])

        col_check, col_content = st.columns([0.06, 0.94])
        with col_check:
            done = st.checkbox("", key=f"step_{customer['id']}_{i}", label_visibility="collapsed")
            if done:
                done_count += 1

        with col_content:
            opacity = "0.4" if done else "1.0"
            decoration = "line-through" if done else "none"
            st.markdown(
                f"""
                <div class="adv-step-card" style="opacity:{opacity};">
                    <div class="adv-step-num">{i}</div>
                    <div>
                        <p class="adv-step-text" style="text-decoration:{decoration};">{step['text']}</p>
                        <span class="adv-step-tag"
                              style="background:{ts['bg']};color:{ts['color']};">
                            {step['tag']}
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Progress bar
    prog_pct = round(done_count / len(customer["steps"]) * 100)
    st.markdown(
        f"""
        <div style="margin-top:6px;padding:10px 0;">
            <div style="display:flex;justify-content:space-between;font-size:11px;
                         color:#a0a1b0;margin-bottom:5px;">
                <span>Actions completed</span>
                <span style="color:#1e1f2e;font-weight:500;">{done_count} of {len(customer['steps'])}</span>
            </div>
            <div class="cw-progress-track">
                <div class="cw-progress-fill" style="width:{prog_pct}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Quick actions ─────────────────────────────────────────────────────────

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p class="cw-section-label">Quick Actions</p>',
        unsafe_allow_html=True,
    )

    driver_label = DRIVER_LABELS.get(customer["top_driver"], customer["top_driver"])

    qa1, qa2, qa3 = st.columns(3)

    with qa1:
        if st.button("📞  Call Script", use_container_width=True):
            st.session_state["advisory_query"] = (
                f"Write a 2-minute personal retention call script for {customer['name']} "
                f"who has a {pct}% churn probability. Their main risk driver is {driver_label}. "
                f"Make it warm, specific, and lead with empathy."
            )

    with qa2:
        if st.button("✉️  Draft Email", use_container_width=True):
            st.session_state["advisory_query"] = (
                f"Draft a short personalised retention email for {customer['name']} "
                f"in the {customer['segment']} segment with {pct}% churn risk. "
                f"Address their {driver_label} issue. Include one specific offer."
            )

    with qa3:
        if st.button("🔄  New Strategy", use_container_width=True):
            st.session_state["advisory_query"] = (
                f"If the first 5 retention steps do not work for {customer['name']}, "
                f"what alternative strategy should be tried? They are {customer['segment']} "
                f"segment with {pct}% churn risk and the main driver is {driver_label}."
            )

    # ── Advisory query input ──────────────────────────────────────────────────

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p class="cw-section-label">Ask the Advisory System</p>',
        unsafe_allow_html=True,
    )

    default_query = st.session_state.get("advisory_query", "")
    query = st.text_input(
        "Query",
        value=default_query,
        placeholder=f"Ask anything about {customer['name']}…",
        label_visibility="collapsed",
    )

    send_col, _ = st.columns([0.15, 0.85])
    with send_col:
        if st.button("Ask →", use_container_width=True):
            if query.strip():
                st.session_state["advisory_query"] = ""
                with st.spinner("Generating advisory response…"):
                    # Placeholder — wire to your advisory agent here
                    st.markdown(
                        f"""
                        <div style="background:#f8fffe;border:1px solid #b0d8d0;border-radius:10px;
                                     padding:16px;margin-top:12px;">
                            <p style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;
                                       color:#4d8a7e;margin:0 0 8px;">Advisory Response</p>
                            <p style="font-size:13px;color:#3a3b50;line-height:1.7;margin:0;">
                                Connect this input to <code>src/advisory/advisory_agent.py</code>
                                to generate a live RAG-powered response for
                                <strong>{customer['name']}</strong>.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.warning("Please enter a question before sending.")
