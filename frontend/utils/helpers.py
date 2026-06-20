# utils/helpers.py

import streamlit as st
import pandas as pd
from pathlib import Path


# ── CSS loader ──────────────────────────────────────────────────────────────

def load_css():
    """Inject the ChurnWatch stylesheet into every page."""
    css_path = Path(__file__).parent.parent / "assets" / "style.css"
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ── Sidebar brand + user ─────────────────────────────────────────────────────

def render_sidebar():
    """Render the ChurnWatch brand header and Admin user block in the sidebar."""
    st.sidebar.markdown(
        """
        <div class="cw-sidebar-brand">
            <div class="cw-logo-box">📊</div>
            <span class="cw-brand-name">ChurnWatch</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<hr class='cw-sb-divider'>", unsafe_allow_html=True)

    st.sidebar.markdown(
        """
        <hr class='cw-sb-divider'>
        <div class="cw-sidebar-user">
            <div class="cw-user-av">AD</div>
            <div>
                <p class="cw-user-name">Admin</p>
                <p class="cw-user-role">System Administrator</p>
            </div>
        </div>
        <p class="cw-sidebar-ver">ChurnWatch v1.0</p>
        """,
        unsafe_allow_html=True,
    )


# ── Mock customer data ────────────────────────────────────────────────────────

RISK_COLORS = {
    "Critical": {"bg": "#fef1ef", "color": "#b85a48", "av_bg": "rgba(192,104,88,0.12)"},
    "High":     {"bg": "#fef5e8", "color": "#b08040", "av_bg": "rgba(192,144,88,0.12)"},
    "Medium":   {"bg": "#eef2fc", "color": "#5a7abf", "av_bg": "rgba(106,143,203,0.12)"},
    "Low":      {"bg": "#edf7f0", "color": "#4a8a5a", "av_bg": "rgba(90,164,100,0.12)"},
}

SEG_COLORS = {
    "Affluent": {"bg": "#f0eeff", "color": "#5848b0"},
    "Mid":      {"bg": "#eef2fc", "color": "#5a7abf"},
    "Mass":     {"bg": "#edf7f0", "color": "#4a8a5a"},
}

DRIVER_LABELS = {
    "activity_drop_flag":   "Inactive member",
    "has_zero_balance":     "Zero account balance",
    "is_single_product":    "Single product only",
    "is_high_risk_support": "Complaint and dissatisfied",
    "low_points":           "Low loyalty engagement",
    "multi_product":        "Multi-product holder",
    "high_engagement":      "High engagement",
    "high_balance":         "High balance customer",
}

RAW_CUSTOMERS = [
    {
        "id": 1, "name": "Rendani Radzuma", "initials": "RR",
        "geography": "Limpopo", "gender": "Male", "age": 45,
        "tenure_months": 36, "salary": 62000, "credit_score": 490,
        "segment": "Mass", "lifecycle": "At-Risk", "card_type": "SILVER",
        "churn_probability": 0.91, "risk_band": "Critical",
        "top_driver": "activity_drop_flag",
        "balance": 0, "num_products": 1, "has_complaint": True,
        "satisfaction_score": 2, "is_active": False, "points": 120,
        "flags": ["activity_drop_flag", "has_zero_balance", "is_single_product", "is_high_risk_support"],
        "why": (
            "Rendani has been completely inactive for over 18 months despite 3 years of tenure, "
            "strongly indicating he has moved his primary banking to a competitor. His account "
            "balance sits at zero, he holds only a single SILVER card, and an unresolved complaint "
            "with a satisfaction score of 2 confirms a poor experience that was never addressed."
        ),
        "steps": [
            {"text": "Call within 24 hours — lead with the complaint, acknowledge the experience, and confirm escalation before any retention offer is made.", "tag": "Call"},
            {"text": "Escalate the open complaint to the branch manager and send a written resolution within 48 hours as a goodwill gesture.", "tag": "Resolve"},
            {"text": "Offer a zero-fee savings account upgrade with a R500 cash-back incentive for transferring any external funds back to the bank.", "tag": "Offer"},
            {"text": "Propose a second product such as a personal loan or funeral cover to increase switching cost and deepen the relationship.", "tag": "Cross-sell"},
            {"text": "Schedule a 7-day follow-up call to confirm complaint resolution and whether funds have returned. Log all contact in the CRM.", "tag": "Follow up"},
        ],
    },
    {
        "id": 2, "name": "Thabo Dlamini", "initials": "TD",
        "geography": "Gauteng", "gender": "Male", "age": 54,
        "tenure_months": 48, "salary": 185000, "credit_score": 720,
        "segment": "Affluent", "lifecycle": "At-Risk", "card_type": "DIAMOND",
        "churn_probability": 0.87, "risk_band": "Critical",
        "top_driver": "activity_drop_flag",
        "balance": 12000, "num_products": 2, "has_complaint": False,
        "satisfaction_score": 3, "is_active": False, "points": 340,
        "flags": ["activity_drop_flag"],
        "why": (
            "Thabo is a high-value Affluent customer who has become fully disengaged despite "
            "4 years of tenure and a DIAMOND card, suggesting he is routing all transactions "
            "through another institution. His neutral satisfaction of 3 out of 5 indicates no "
            "compelling reason to stay without a personal relationship intervention."
        ),
        "steps": [
            {"text": "Assign a senior relationship manager immediately — personal service is the strongest retention lever for Affluent customers.", "tag": "Escalate"},
            {"text": "Schedule an exclusive in-branch consultation to review DIAMOND benefits and present investment portfolio options.", "tag": "Call"},
            {"text": "Offer a complimentary travel insurance upgrade and extended airport lounge access as immediate goodwill.", "tag": "Offer"},
            {"text": "Present a tax-free savings or unit trust product to deepen the relationship and raise switching costs.", "tag": "Cross-sell"},
            {"text": "Set a quarterly executive review call. Document all contact and schedule a 14-day check-in.", "tag": "Follow up"},
        ],
    },
    {
        "id": 3, "name": "Sello Mahlangu", "initials": "SM",
        "geography": "Mpumalanga", "gender": "Male", "age": 41,
        "tenure_months": 30, "salary": 72000, "credit_score": 510,
        "segment": "Mass", "lifecycle": "At-Risk", "card_type": "SILVER",
        "churn_probability": 0.79, "risk_band": "High",
        "top_driver": "is_high_risk_support",
        "balance": 5000, "num_products": 1, "has_complaint": True,
        "satisfaction_score": 2, "is_active": False, "points": 180,
        "flags": ["is_high_risk_support", "is_single_product"],
        "why": (
            "Sello has an active complaint combined with a very low satisfaction score of 2, "
            "which is the strongest predictor of imminent churn in his profile. As a Mass "
            "customer holding only one SILVER product, he has minimal financial commitment "
            "and will leave if the complaint is not resolved quickly."
        ),
        "steps": [
            {"text": "Resolve the open complaint within 48 hours and get a reference number to share with Sello at the start of the retention call.", "tag": "Resolve"},
            {"text": "Call Sello personally with a branch manager apology and confirm the complaint has been escalated and closed.", "tag": "Call"},
            {"text": "Offer a fee waiver or cash-back gesture as compensation for the negative service experience.", "tag": "Offer"},
            {"text": "Present a second product at a preferential rate to deepen the relationship once the complaint is resolved.", "tag": "Cross-sell"},
            {"text": "Follow up in 7 days to confirm satisfaction has improved and document the outcome in the CRM.", "tag": "Follow up"},
        ],
    },
    {
        "id": 4, "name": "Naledi Mokoena", "initials": "NM",
        "geography": "Western Cape", "gender": "Female", "age": 43,
        "tenure_months": 36, "salary": 95000, "credit_score": 580,
        "segment": "Mid", "lifecycle": "At-Risk", "card_type": "GOLD",
        "churn_probability": 0.74, "risk_band": "High",
        "top_driver": "has_zero_balance",
        "balance": 0, "num_products": 1, "has_complaint": False,
        "satisfaction_score": 3, "is_active": True, "points": 280,
        "flags": ["has_zero_balance", "is_single_product"],
        "why": (
            "Naledi has drained her account to zero while still technically active, a clear "
            "sign she is transitioning her primary banking to a competitor but has not yet "
            "formally closed the account. Her 3-year tenure represents a valuable but rapidly "
            "closing retention window."
        ),
        "steps": [
            {"text": "Call within 24 hours and ask directly whether she has moved her banking — listen before making any offer.", "tag": "Call"},
            {"text": "Present a competitive 30-day notice savings account with a promotional interest rate.", "tag": "Offer"},
            {"text": "Offer a GOLD card fee waiver for 6 months and double loyalty points on all transactions for 90 days.", "tag": "Offer"},
            {"text": "Propose a credit facility or household insurance as a second product at a preferential Mid-segment rate.", "tag": "Cross-sell"},
            {"text": "Set a 10-day check-in to confirm whether funds have returned and a second product is being considered.", "tag": "Follow up"},
        ],
    },
    {
        "id": 5, "name": "Palesa Motsepe", "initials": "PM",
        "geography": "Free State", "gender": "Female", "age": 27,
        "tenure_months": 6, "salary": 45000, "credit_score": 420,
        "segment": "Mass", "lifecycle": "New", "card_type": "SILVER",
        "churn_probability": 0.61, "risk_band": "High",
        "top_driver": "has_zero_balance",
        "balance": 0, "num_products": 1, "has_complaint": False,
        "satisfaction_score": 3, "is_active": True, "points": 60,
        "flags": ["has_zero_balance", "is_single_product"],
        "why": (
            "Palesa opened her account 6 months ago but has never deposited a meaningful "
            "balance, suggesting she trialled the bank but conducts her primary banking "
            "elsewhere. As a young Mass segment customer she is highly price-sensitive and "
            "will not stay without a compelling financial reason."
        ),
        "steps": [
            {"text": "Schedule a welcome check-in call — frame it as a check on her banking experience, not a sales call.", "tag": "Call"},
            {"text": "Offer a cash incentive for her first salary deposit or a zero-fee transaction period for 3 months.", "tag": "Offer"},
            {"text": "Present the youth starter savings product and demonstrate how it builds a credit history.", "tag": "Offer"},
            {"text": "Walk her through the loyalty rewards programme and what she is currently missing.", "tag": "Call"},
            {"text": "Set a 30-day check-in to see whether any transactions have occurred and rewards have started.", "tag": "Follow up"},
        ],
    },
    {
        "id": 6, "name": "Zanele Nkosi", "initials": "ZN",
        "geography": "Limpopo", "gender": "Female", "age": 29,
        "tenure_months": 8, "salary": 52000, "credit_score": 460,
        "segment": "Mass", "lifecycle": "New", "card_type": "SILVER",
        "churn_probability": 0.55, "risk_band": "Medium",
        "top_driver": "is_high_risk_support",
        "balance": 8000, "num_products": 1, "has_complaint": True,
        "satisfaction_score": 2, "is_active": True, "points": 90,
        "flags": ["is_high_risk_support"],
        "why": (
            "Zanele has lodged a complaint within her first 8 months, which is an early "
            "warning sign that her initial banking experience has been negative. With a "
            "satisfaction score of 2 and a single product, she has not yet built a "
            "relationship that would give her a reason to stay."
        ),
        "steps": [
            {"text": "Resolve the complaint immediately and personally confirm closure with Zanele before any retention conversation.", "tag": "Resolve"},
            {"text": "Offer a new customer goodwill gesture such as a fee rebate or bonus loyalty points.", "tag": "Offer"},
            {"text": "Assign a dedicated new-customer advisor to guide her through the product range.", "tag": "Escalate"},
            {"text": "Present a second product suited to her income and age group.", "tag": "Cross-sell"},
            {"text": "Check in again in 2 weeks to confirm satisfaction has recovered.", "tag": "Follow up"},
        ],
    },
    {
        "id": 7, "name": "Kagiso Khumalo", "initials": "KK",
        "geography": "Mpumalanga", "gender": "Male", "age": 38,
        "tenure_months": 24, "salary": 78000, "credit_score": 540,
        "segment": "Mid", "lifecycle": "Growing", "card_type": "SILVER",
        "churn_probability": 0.42, "risk_band": "Medium",
        "top_driver": "low_points",
        "balance": 22000, "num_products": 2, "has_complaint": False,
        "satisfaction_score": 4, "is_active": True, "points": 210,
        "flags": ["low_points"],
        "why": (
            "Kagiso has been with the bank for 2 years and is active, but his low loyalty "
            "points relative to tenure suggest he is not engaging deeply. This disengagement "
            "pattern, while not yet critical, indicates he may be banking elsewhere for "
            "day-to-day needs."
        ),
        "steps": [
            {"text": "Send a personalised loyalty statement showing the rewards he has missed by not transacting more actively.", "tag": "Call"},
            {"text": "Offer a loyalty points bonus for the next 3 months to incentivise deeper daily engagement.", "tag": "Offer"},
            {"text": "Schedule a product review to ensure he is on the right product tier for his income.", "tag": "Call"},
            {"text": "Present a credit facility or investment account as a third product.", "tag": "Cross-sell"},
            {"text": "Follow up in 30 days to check whether engagement and points activity have increased.", "tag": "Follow up"},
        ],
    },
    {
        "id": 8, "name": "Ntombi Majola", "initials": "NM2",
        "geography": "Western Cape", "gender": "Female", "age": 36,
        "tenure_months": 12, "salary": 115000, "credit_score": 640,
        "segment": "Mid", "lifecycle": "New", "card_type": "GOLD",
        "churn_probability": 0.38, "risk_band": "Medium",
        "top_driver": "is_single_product",
        "balance": 31000, "num_products": 1, "has_complaint": False,
        "satisfaction_score": 4, "is_active": True, "points": 320,
        "flags": ["is_single_product"],
        "why": (
            "Ntombi has been a customer for 12 months but holds only one product despite "
            "qualifying for several Mid-segment offerings. This represents a missed "
            "cross-sell opportunity, and a single-product customer is significantly "
            "easier for a competitor to poach."
        ),
        "steps": [
            {"text": "Schedule a one-year anniversary check-in call and use it to open the cross-sell conversation.", "tag": "Call"},
            {"text": "Present a bundled product offer with a fee discount for adding a second GOLD-tier product.", "tag": "Offer"},
            {"text": "Walk her through the savings or investment products suited to her income bracket.", "tag": "Offer"},
            {"text": "Demonstrate the loyalty benefits increase when holding two or more products.", "tag": "Call"},
            {"text": "Follow up in 14 days to confirm whether a second product application has been submitted.", "tag": "Follow up"},
        ],
    },
    {
        "id": 9, "name": "Johan Pretorius", "initials": "JP",
        "geography": "Gauteng", "gender": "Male", "age": 51,
        "tenure_months": 60, "salary": 195000, "credit_score": 730,
        "segment": "Affluent", "lifecycle": "Growing", "card_type": "DIAMOND",
        "churn_probability": 0.22, "risk_band": "Low",
        "top_driver": "multi_product",
        "balance": 85000, "num_products": 3, "has_complaint": False,
        "satisfaction_score": 5, "is_active": True, "points": 780,
        "flags": [],
        "why": (
            "Johan is a stable long-tenured Affluent customer with three products, a DIAMOND "
            "card, and maximum satisfaction. His low churn risk reflects deep product loyalty. "
            "Standard relationship manager contact is sufficient to maintain his engagement."
        ),
        "steps": [
            {"text": "Schedule a quarterly relationship review to confirm all financial needs are being met at the Affluent tier.", "tag": "Call"},
            {"text": "Present any new DIAMOND tier benefits or investment products launched in the last 12 months.", "tag": "Offer"},
            {"text": "Explore whether he has estate planning or business banking needs the bank can serve.", "tag": "Call"},
            {"text": "Confirm all DIAMOND lounge and travel benefits are active and in use.", "tag": "Call"},
            {"text": "Log the interaction and schedule the next quarterly review in 90 days.", "tag": "Follow up"},
        ],
    },
    {
        "id": 10, "name": "Lindiwe Cele", "initials": "LC",
        "geography": "Free State", "gender": "Female", "age": 47,
        "tenure_months": 60, "salary": 165000, "credit_score": 690,
        "segment": "Affluent", "lifecycle": "Growing", "card_type": "GOLD",
        "churn_probability": 0.18, "risk_band": "Low",
        "top_driver": "high_engagement",
        "balance": 62000, "num_products": 2, "has_complaint": False,
        "satisfaction_score": 5, "is_active": True, "points": 650,
        "flags": [],
        "why": (
            "Lindiwe is a well-engaged Affluent customer who actively uses her GOLD card and "
            "has maintained a 5-year relationship with strong satisfaction. Her low churn risk "
            "reflects consistent product loyalty. The primary opportunity is upgrading her to "
            "DIAMOND status."
        ),
        "steps": [
            {"text": "Send a personalised 5-year loyalty appreciation message from the branch manager.", "tag": "Call"},
            {"text": "Present the upgrade pathway to DIAMOND status given her income and engagement level.", "tag": "Offer"},
            {"text": "Explore any financial planning needs for the coming 12 months.", "tag": "Call"},
            {"text": "Offer early access to any new Affluent product launches.", "tag": "Offer"},
            {"text": "Schedule a 6-month check-in with the relationship manager.", "tag": "Follow up"},
        ],
    },
    {
        "id": 11, "name": "Sipho van der Merwe", "initials": "SV",
        "geography": "Gauteng", "gender": "Male", "age": 62,
        "tenure_months": 72, "salary": 210000, "credit_score": 750,
        "segment": "Affluent", "lifecycle": "Growing", "card_type": "PLATINUM",
        "churn_probability": 0.15, "risk_band": "Low",
        "top_driver": "multi_product",
        "balance": 120000, "num_products": 3, "has_complaint": False,
        "satisfaction_score": 5, "is_active": True, "points": 920,
        "flags": [],
        "why": (
            "Sipho is a deeply loyal long-tenured Affluent customer with three products "
            "and a PLATINUM card. His very low churn risk is supported by near-perfect "
            "engagement. Proactive relationship management is all that is required."
        ),
        "steps": [
            {"text": "Acknowledge his 6-year tenure with a personalised loyalty recognition gesture.", "tag": "Call"},
            {"text": "Schedule an annual financial wellness review.", "tag": "Call"},
            {"text": "Present any new PLATINUM or private banking products.", "tag": "Offer"},
            {"text": "Ensure all PLATINUM benefits are up to date and actively used.", "tag": "Call"},
            {"text": "Schedule a 6-month follow-up with the relationship manager.", "tag": "Follow up"},
        ],
    },
    {
        "id": 12, "name": "Amahle Zulu", "initials": "AZ",
        "geography": "Northern Cape", "gender": "Female", "age": 58,
        "tenure_months": 84, "salary": 240000, "credit_score": 800,
        "segment": "Affluent", "lifecycle": "Growing", "card_type": "DIAMOND",
        "churn_probability": 0.09, "risk_band": "Low",
        "top_driver": "high_balance",
        "balance": 180000, "num_products": 4, "has_complaint": False,
        "satisfaction_score": 5, "is_active": True, "points": 1100,
        "flags": [],
        "why": (
            "Amahle is the bank's lowest-risk customer — a long-tenured, high-balance "
            "Affluent customer with four products, a DIAMOND card, and an outstanding "
            "credit score. Her minimal churn probability and deep product loyalty make "
            "her an exemplary VIP relationship to maintain and protect."
        ),
        "steps": [
            {"text": "Arrange an exclusive DIAMOND tier private banking experience or invitation event.", "tag": "Offer"},
            {"text": "Schedule a bespoke investment portfolio review given her high balance and tenure.", "tag": "Call"},
            {"text": "Present wealth management or estate planning services at the DIAMOND tier.", "tag": "Offer"},
            {"text": "Confirm she has a dedicated private banker relationship and direct contact line.", "tag": "Escalate"},
            {"text": "Schedule a quarterly VIP review and add to the priority retention watchlist.", "tag": "Follow up"},
        ],
    },
]


def get_customers_df() -> pd.DataFrame:
    """Return customers as a display-ready DataFrame."""
    rows = []
    for c in RAW_CUSTOMERS:
        rows.append({
            "Name":       c["name"],
            "Segment":    c["segment"],
            "Province":   c["geography"],
            "Risk Band":  c["risk_band"],
            "Score":      f"{round(c['churn_probability'] * 100)}%",
            "Card":       c["card_type"],
            "Tenure":     f"{c['tenure_months']} mo",
            "Top Driver": DRIVER_LABELS.get(c["top_driver"], c["top_driver"]),
        })
    return pd.DataFrame(rows)


def get_customer_by_name(name: str) -> dict | None:
    for c in RAW_CUSTOMERS:
        if c["name"] == name:
            return c
    return None


def get_customer_names() -> list[str]:
    return [c["name"] for c in RAW_CUSTOMERS]


# ── Tag styling ───────────────────────────────────────────────────────────────

STEP_TAG_STYLES = {
    "Call":       {"bg": "#eef2fc", "color": "#5a7abf"},
    "Resolve":    {"bg": "#fef1ef", "color": "#b85a48"},
    "Offer":      {"bg": "#edf7f0", "color": "#4a8a5a"},
    "Cross-sell": {"bg": "#fef5e8", "color": "#b08040"},
    "Follow up":  {"bg": "#f0eeff", "color": "#5848b0"},
    "Escalate":   {"bg": "#f4f4f8", "color": "#6b6c80"},
}
