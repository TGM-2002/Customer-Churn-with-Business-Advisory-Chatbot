# pages/1_Dashboard.py  Portfolio overview with SOM visualisations
# The main analytics page. Shows KPI tiles at the top that update when the user
# switches between Week / Month / Year. Below the KPIs, three tabs hold the
# Overview (highlights + at-risk table), the SOM Customer Map (three heatmaps),
# and the Risk Analysis charts (province, segment, trend).

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from utils.helpers import load_css, render_sidebar, RAW_CUSTOMERS, RISK_COLORS

st.set_page_config(
    page_title="CRS — Dashboard",
    page_icon=":material/bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
render_sidebar()

BASE = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter,-apple-system,sans-serif", color="#1a1826", size=10),
    margin=dict(t=8, b=8, l=8, r=8),
)

# Period data 
# Stores the KPI numbers and chart data for each time period (Week, Month, Year).
# When the user picks a period, the page reads from the matching key in this dictionary.

PERIOD = {
    "Week": {
        "total": "2,847", "at_risk": "436",  "churn_rate": "15.3%", "revenue": "R12.4M",
        "d_total": "+12 this week",         "d_risk": "+5 from last week",
        "d_rate": "+0.1pp this week",        "d_rev": "Up R0.3M from last week",
        "prov_rates":  [73, 61, 56, 40, 40, 9],
        "seg_scores":  [72, 51, 38],
        "trend":       [44, 46, 44, 48, 51, 47, 43],
        "trend_x":     ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "trend_title": "Average churn probability — current week",
        "donut":       [17, 25, 25, 33],
        "highlights": [
            ("3", "Critical accounts", "#dc2626", "#fef2f2"),
            ("4", "High risk accounts", "#ea580c", "#fff7ed"),
            ("73%", "Highest province (Limpopo)", "#d97706", "#fffbeb"),
            ("7", "Require action this week", "#7c3aed", "#f5f3ff"),
        ],
    },
    "Month": {
        "total": "2,847", "at_risk": "436",  "churn_rate": "15.3%", "revenue": "R12.4M",
        "d_total": "+124 this month",       "d_risk": "+38 from last month",
        "d_rate": "+0.4pp month-on-month",  "d_rev": "Critical attention needed",
        "prov_rates":  [73, 61, 56, 40, 40, 9],
        "seg_scores":  [72, 51, 38],
        "trend":       [32, 35, 31, 38, 42, 46, 44, 48, 51, 47, 43, 46],
        "trend_x":     ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
        "trend_title": "Average churn probability trend — 2025/2026",
        "donut":       [17, 25, 25, 33],
        "highlights": [
            ("436", "Customers at risk", "#dc2626", "#fef2f2"),
            ("R12.4M", "Revenue at risk", "#ea580c", "#fff7ed"),
            ("+38", "New at-risk this month", "#d97706", "#fffbeb"),
            ("2", "Customers improved", "#16a34a", "#f0fdf4"),
        ],
    },
    "Year": {
        "total": "2,847", "at_risk": "580",  "churn_rate": "20.4%", "revenue": "R18.7M",
        "d_total": "+1,240 YoY",            "d_risk": "+144 from prior year",
        "d_rate": "+5.1pp year-on-year",    "d_rev": "Up R6.3M from prior year",
        "prov_rates":  [68, 57, 52, 36, 35, 7],
        "seg_scores":  [69, 48, 35],
        "trend":       [11, 12, 13, 14, 15, 16, 15, 16, 16, 16, 15, 15],
        "trend_x":     ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
        "trend_title": "Average churn probability — 2025/2026 full year",
        "donut":       [20, 27, 23, 30],
        "highlights": [
            ("580", "Customers at risk (YTD)", "#dc2626", "#fef2f2"),
            ("R18.7M", "Revenue at risk (YTD)", "#ea580c", "#fff7ed"),
            ("+144", "More at-risk vs prior year", "#d97706", "#fffbeb"),
            ("20.4%", "Portfolio churn rate", "#7c3aed", "#f5f3ff"),
        ],
    },
}

#  SOM data 
# Builds mock SOM grid data used to draw the Customer Map tab.
# In production this would come from the trained SOM in src/som/som_core.py.
# The three grids (u_mat, churn_mat, scatter points) power the three charts in that tab.

np.random.seed(42)
GRID = 8
axis_labels = [str(i) for i in range(GRID)]

u_mat = np.random.uniform(0.4, 0.65, (GRID, GRID))
u_mat[0:3, 0:3] = np.random.uniform(0.05, 0.16, (3, 3))
u_mat[2:5, 2:5] = np.random.uniform(0.25, 0.40, (3, 3))
u_mat[3:6, 4:7] = np.random.uniform(0.14, 0.26, (3, 3))
u_mat[5:8, 5:8] = np.random.uniform(0.05, 0.16, (3, 3))
u_mat[2, :]     = np.random.uniform(0.78, 0.94, GRID)
u_mat[:, 4]     = np.random.uniform(0.72, 0.90, GRID)
u_mat           = np.clip(u_mat + np.random.uniform(-0.04, 0.04, (GRID, GRID)), 0, 1)

churn_mat = np.random.uniform(0.25, 0.52, (GRID, GRID))
churn_mat[0:3, 0:3] = np.random.uniform(0.04, 0.17, (3, 3))
churn_mat[2:5, 2:5] = np.random.uniform(0.35, 0.50, (3, 3))
churn_mat[3:6, 4:7] = np.random.uniform(0.58, 0.75, (3, 3))
churn_mat[5:8, 5:8] = np.random.uniform(0.78, 0.95, (3, 3))
churn_mat           = np.clip(churn_mat + np.random.uniform(-0.03, 0.03, (GRID, GRID)), 0, 1)

BAND_COLOR = {"Critical": "#dc2626", "High": "#ea580c", "Medium": "#d97706", "Low": "#16a34a"}
BAND_ZONE  = {
    "Critical": (5.0, 7.5, 5.0, 7.5), "High":  (3.5, 6.0, 4.0, 6.5),
    "Medium":   (2.0, 5.0, 2.0, 5.0), "Low":   (0.1, 2.8, 0.1, 2.8),
}
bmu_x, bmu_y, dot_colors, dot_names, dot_probs = [], [], [], [], []
for c in RAW_CUSTOMERS:
    x0, x1, y0, y1 = BAND_ZONE[c["risk_band"]]
    bmu_x.append(np.clip(np.random.uniform(x0, x1) + np.random.uniform(-0.25, 0.25), 0, 7.9))
    bmu_y.append(np.clip(np.random.uniform(y0, y1) + np.random.uniform(-0.25, 0.25), 0, 7.9))
    dot_colors.append(BAND_COLOR[c["risk_band"]])
    dot_names.append(c["name"])
    dot_probs.append(round(c["churn_probability"] * 100))

#  Header + period 
# Page title on the left, Week / Month / Year radio buttons on the right.
# Whatever the user picks here controls which numbers appear in all sections below.

hdr_col, period_col = st.columns([2, 1])
with hdr_col:
    st.markdown(
        '<div class="cw-page-header">'
        '<p class="cw-page-title">Dashboard</p>'
        '<p class="cw-page-subtitle">Portfolio overview · 15 Jun 2026</p>'
        '</div>',
        unsafe_allow_html=True,
    )
with period_col:
    st.markdown("<div style='padding-top:10px;'>", unsafe_allow_html=True)
    period = st.radio("Period", ["Week", "Month", "Year"], index=1,
                      horizontal=True, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

p = PERIOD[period]

#  KPIs (always visible) 
# Four metric tiles that always show regardless of which tab is open.
# The numbers update automatically when the period changes above.

k1, k2, k3, k4 = st.columns(4, gap="medium")
k1.metric("Total Customers",  p["total"],      p["d_total"])
k2.metric("At Risk",          p["at_risk"],    p["d_risk"],   delta_color="inverse")
k3.metric("Churn Rate",       p["churn_rate"], p["d_rate"],   delta_color="inverse")
k4.metric("Revenue at Risk",  p["revenue"],    p["d_rev"],    delta_color="inverse")

st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

#Tabs
# Three folders the user can click between:
#   Overview      :text highlights and the at-risk customer table
#   Customer Map  :SOM heatmaps showing how customers cluster on the grid
#   Risk Analysis : bar charts, donut chart, and a trend line by province/segment

tab_overview, tab_som, tab_risk = st.tabs([
    "Overview",
    "Customer Map  (SOM)",
    "Risk Analysis",
])


# TAB 1 :Overview 


with tab_overview:
    # Highlight stat tiles
    st.markdown('<p class="cw-section-label">Key Highlights</p>', unsafe_allow_html=True)
    h1, h2, h3, h4 = st.columns(4, gap="medium")
    for col, (val, label, color, bg) in zip([h1, h2, h3, h4], p["highlights"]):
        with col:
            st.markdown(
                f"""
                <div style="background:{bg};border:1px solid {color}22;border-radius:12px;
                             padding:20px;text-align:center;">
                    <p style="font-size:28px;font-weight:300;color:{color};margin:0 0 4px;">{val}</p>
                    <p style="font-size:11px;color:#6b6484;margin:0;line-height:1.5;">{label}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    # At-risk customers table
    st.markdown('<p class="cw-section-label">At-Risk Customers — Ranked by Churn Probability</p>',
                unsafe_allow_html=True)

    from utils.helpers import DRIVER_LABELS
    at_risk = sorted(
        [c for c in RAW_CUSTOMERS if c["risk_band"] in ("Critical", "High", "Medium")],
        key=lambda c: -c["churn_probability"],
    )

    table_data = pd.DataFrame([{
        "Customer":    c["name"],
        "Risk Band":   c["risk_band"],
        "Score":       f"{round(c['churn_probability']*100)}%",
        "Top Driver":  DRIVER_LABELS.get(c["top_driver"], c["top_driver"]),
        "Segment":     c["segment"],
        "Province":    c["geography"],
    } for c in at_risk])

    st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    if st.button("View all customers in detail", use_container_width=False):
        st.switch_page("pages/2_Customers.py")


# TAB 2: Customer Map (SOM)


with tab_som:
    st.markdown('<p class="cw-section-label">Self-Organizing Map — Customer Segmentation</p>',
                unsafe_allow_html=True)
    rc1, rc2, rc3 = st.columns(3, gap="medium")

    with rc1:
        st.markdown('<div class="cw-card">', unsafe_allow_html=True)
        st.markdown('<p class="cw-card-title">U-Matrix — Neuron Distance Map</p>', unsafe_allow_html=True)
        fig_um = go.Figure(go.Heatmap(
            z=u_mat,
            colorscale=[[0,"#faf8ff"],[0.25,"#e9d5ff"],[0.55,"#a855f7"],[0.80,"#5b21b6"],[1,"#1e0a45"]],
            zmin=0, zmax=1,
            colorbar=dict(thickness=8, len=0.8, tickfont=dict(size=8)),
            hovertemplate="Cell (%{x},%{y})<br>Distance: %{z:.2f}<extra></extra>",
        ))
        fig_um.update_layout(
            **BASE, height=220,
            xaxis=dict(tickvals=list(range(GRID)), ticktext=axis_labels, tickfont=dict(size=8), showgrid=False),
            yaxis=dict(tickvals=list(range(GRID)), ticktext=axis_labels, tickfont=dict(size=8), showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig_um, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<p style="font-size:10px;color:#9992b0;margin:0;">Dark = cluster boundary · Light = cluster centre</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with rc2:
        st.markdown('<div class="cw-card">', unsafe_allow_html=True)
        st.markdown('<p class="cw-card-title">Churn Rate per SOM Cell</p>', unsafe_allow_html=True)
        fig_ch = go.Figure(go.Heatmap(
            z=churn_mat,
            colorscale=[[0,"#f0fdf4"],[0.35,"#86efac"],[0.6,"#f59e0b"],[0.8,"#ea580c"],[1,"#dc2626"]],
            zmin=0, zmax=1,
            colorbar=dict(thickness=8, len=0.8, tickvals=[0,0.3,0.6,0.8,1],
                          ticktext=["0%","30%","60%","80%","100%"], tickfont=dict(size=8)),
            hovertemplate="Cell (%{x},%{y})<br>Churn Rate: %{z:.0%}<extra></extra>",
        ))
        fig_ch.update_layout(
            **BASE, height=220,
            xaxis=dict(tickvals=list(range(GRID)), ticktext=axis_labels, tickfont=dict(size=8), showgrid=False),
            yaxis=dict(tickvals=list(range(GRID)), ticktext=axis_labels, tickfont=dict(size=8), showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig_ch, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<p style="font-size:10px;color:#9992b0;margin:0;">Red = high churn risk · Green = low churn risk</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with rc3:
        st.markdown('<div class="cw-card">', unsafe_allow_html=True)
        st.markdown('<p class="cw-card-title">Customer Risk Clusters on SOM</p>', unsafe_allow_html=True)
        fig_sc = go.Figure()
        for band, color in BAND_COLOR.items():
            mask = [c["risk_band"] == band for c in RAW_CUSTOMERS]
            x_b  = [bmu_x[i] for i, m in enumerate(mask) if m]
            y_b  = [bmu_y[i] for i, m in enumerate(mask) if m]
            n_b  = [dot_names[i] for i, m in enumerate(mask) if m]
            p_b  = [dot_probs[i] for i, m in enumerate(mask) if m]
            fig_sc.add_trace(go.Scatter(
                x=x_b, y=y_b, mode="markers", name=band,
                marker=dict(color=color, size=[8 + pp/15 for pp in p_b], opacity=0.85,
                            line=dict(color="white", width=1)),
                text=[f"{n}<br>{band} — {pp}%" for n, pp in zip(n_b, p_b)],
                hovertemplate="%{text}<extra></extra>",
            ))
        fig_sc.update_layout(
            **BASE, height=220,
            xaxis=dict(title="SOM Column", range=[-0.3,8.0], showgrid=True, gridcolor="#f2effb", tickfont=dict(size=8)),
            yaxis=dict(title="SOM Row",    range=[-0.3,8.0], showgrid=True, gridcolor="#f2effb", tickfont=dict(size=8)),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(size=9)),
        )
        st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<p style="font-size:10px;color:#9992b0;margin:0;">Marker size proportional to churn probability</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# TAB 3 : Risk Analysis


with tab_risk:
    st.markdown('<p class="cw-section-label">Churn Analysis by Geography, Risk Band and Segment</p>',
                unsafe_allow_html=True)
    ra1, ra2, ra3 = st.columns(3, gap="medium")

    with ra1:
        st.markdown('<div class="cw-card">', unsafe_allow_html=True)
        st.markdown('<p class="cw-card-title">Churn rate by province</p>', unsafe_allow_html=True)
        prov_df = pd.DataFrame({
            "Province": ["Limpopo","Mpumalanga","W. Cape","Gauteng","Free State","N. Cape"],
            "Rate":     p["prov_rates"],
            "Color":    ["#dc2626","#ea580c","#ea580c","#d97706","#d97706","#16a34a"],
        })
        fig_pv = go.Figure(go.Bar(
            x=prov_df["Rate"], y=prov_df["Province"], orientation="h",
            marker_color=prov_df["Color"],
            text=prov_df["Rate"].apply(lambda v: f"{v}%"),
            textposition="outside", cliponaxis=False,
            hovertemplate="%{y}: %{x}%<extra></extra>",
        ))
        fig_pv.update_layout(**BASE, height=220,
            xaxis=dict(visible=False, range=[0,95]),
            yaxis=dict(tickfont=dict(size=10, color="#6b6484")), bargap=0.38)
        st.plotly_chart(fig_pv, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with ra2:
        st.markdown('<div class="cw-card">', unsafe_allow_html=True)
        st.markdown('<p class="cw-card-title">Risk band distribution</p>', unsafe_allow_html=True)
        fig_rng = go.Figure(go.Pie(
            labels=["Critical","High","Medium","Low"], values=p["donut"],
            hole=0.60, marker_colors=["#dc2626","#ea580c","#d97706","#16a34a"],
            textinfo="label+percent", textfont=dict(size=10),
            hovertemplate="<b>%{label}</b>: %{percent}<extra></extra>",
        ))
        fig_rng.add_annotation(text=f"<b>{p['total']}</b>", x=0.5, y=0.5, showarrow=False,
                                font=dict(size=13, color="#1a1826"))
        fig_rng.update_layout(**BASE, height=220, showlegend=False)
        st.plotly_chart(fig_rng, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with ra3:
        st.markdown('<div class="cw-card">', unsafe_allow_html=True)
        st.markdown('<p class="cw-card-title">Avg churn score by segment</p>', unsafe_allow_html=True)
        seg_df = pd.DataFrame({
            "Segment": ["Mass","Mid","Affluent"],
            "Score":   p["seg_scores"],
            "Color":   ["#dc2626","#ea580c","#d97706"],
        })
        fig_sg = go.Figure(go.Bar(
            x=seg_df["Segment"], y=seg_df["Score"],
            marker_color=seg_df["Color"], marker_cornerradius=4,
            text=seg_df["Score"].apply(lambda v: f"{v}%"),
            textposition="outside", cliponaxis=False,
            hovertemplate="%{x}: %{y}%<extra></extra>",
        ))
        fig_sg.update_layout(**BASE, height=220,
            xaxis=dict(tickfont=dict(size=11, color="#6b6484"), showgrid=False),
            yaxis=dict(visible=False, range=[0,90]), bargap=0.45)
        st.plotly_chart(fig_sg, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # Trend line
    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    st.markdown('<p class="cw-section-label">Churn Probability Trend</p>', unsafe_allow_html=True)

    trend_df = pd.DataFrame({"x": p["trend_x"], "y": p["trend"]})
    fig_tr = go.Figure()
    fig_tr.add_trace(go.Scatter(
        x=trend_df["x"], y=trend_df["y"],
        mode="lines+markers",
        line=dict(color="#7c3aed", width=2.5),
        marker=dict(color="#7c3aed", size=5, line=dict(color="white", width=1.5)),
        fill="tozeroy", fillcolor="rgba(124,58,237,0.07)",
        hovertemplate="%{x}: %{y}%<extra></extra>",
    ))
    fig_tr.add_hline(y=sum(p["trend"]) / len(p["trend"]),
        line=dict(dash="dot", color="#e8e3f2", width=1),
        annotation_text=f"  avg {round(sum(p['trend'])/len(p['trend']))}%",
        annotation_font=dict(size=9, color="#9992b0"))
    fig_tr.update_layout(**BASE, height=160,
        xaxis=dict(tickfont=dict(size=10, color="#9992b0"), showgrid=False),
        yaxis=dict(tickfont=dict(size=10, color="#9992b0"), ticksuffix="%",
                   gridcolor="#f2effb", range=[0,65], zeroline=False),
        showlegend=False)
    st.markdown('<div class="cw-card">', unsafe_allow_html=True)
    st.markdown(f'<p class="cw-card-title">{p["trend_title"]}</p>', unsafe_allow_html=True)
    st.plotly_chart(fig_tr, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
