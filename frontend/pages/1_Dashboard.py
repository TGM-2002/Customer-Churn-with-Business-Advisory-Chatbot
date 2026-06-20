# pages/1_Dashboard.py  —  Portfolio overview with SOM visualisations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from utils.helpers import load_css, render_sidebar, RAW_CUSTOMERS, RISK_COLORS

st.set_page_config(
    page_title="ChurnWatch — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
render_sidebar()

BASE = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter,-apple-system,sans-serif", color="#1e1f2e", size=10),
    margin=dict(t=8, b=8, l=8, r=8),
)

# ── Simulated SOM data ─────────────────────────────────────────────────────────
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

BAND_COLOR = {"Critical": "#c06858", "High": "#c09058", "Medium": "#6a8fcb", "Low": "#5a9a6a"}
BAND_ZONE  = {
    "Critical": (5.0, 7.5, 5.0, 7.5),
    "High":     (3.5, 6.0, 4.0, 6.5),
    "Medium":   (2.0, 5.0, 2.0, 5.0),
    "Low":      (0.1, 2.8, 0.1, 2.8),
}
bmu_x, bmu_y, dot_colors, dot_names, dot_probs = [], [], [], [], []
for c in RAW_CUSTOMERS:
    x0, x1, y0, y1 = BAND_ZONE[c["risk_band"]]
    bmu_x.append(np.clip(np.random.uniform(x0, x1) + np.random.uniform(-0.25, 0.25), 0, 7.9))
    bmu_y.append(np.clip(np.random.uniform(y0, y1) + np.random.uniform(-0.25, 0.25), 0, 7.9))
    dot_colors.append(BAND_COLOR[c["risk_band"]])
    dot_names.append(c["name"])
    dot_probs.append(round(c["churn_probability"] * 100))

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="cw-page-header">'
    '<p class="cw-page-title">Dashboard</p>'
    '<p class="cw-page-subtitle">Portfolio overview · 15 Jun 2026</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Customers",  "2,847", "+124 this month")
k2.metric("At Risk",          "436",   "+38 from last month",        delta_color="inverse")
k3.metric("Churn Rate",       "15.3%", "+0.4pp month-on-month",      delta_color="inverse")
k4.metric("Revenue at Risk",  "R12.4M", "Critical attention needed", delta_color="inverse")

st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)

# ── ROW 1 — SOM Visualisations ─────────────────────────────────────────────────
st.markdown('<p class="cw-section-label">Self-Organizing Map — Customer Segmentation</p>', unsafe_allow_html=True)
rc1, rc2, rc3 = st.columns(3)

with rc1:
    st.markdown('<div class="cw-card">', unsafe_allow_html=True)
    st.markdown('<p class="cw-card-title">U-Matrix — Neuron Distance Map</p>', unsafe_allow_html=True)
    fig_um = go.Figure(go.Heatmap(
        z=u_mat,
        colorscale=[[0,"#f0faf8"],[0.3,"#9ecfc6"],[0.6,"#4d8a7e"],[0.85,"#2d4a46"],[1,"#1a2e2c"]],
        zmin=0, zmax=1,
        colorbar=dict(thickness=8, len=0.8, tickfont=dict(size=8)),
        hovertemplate="Cell (%{x},%{y})<br>Distance: %{z:.2f}<extra></extra>",
    ))
    fig_um.update_layout(
        **BASE, height=205,
        xaxis=dict(tickvals=list(range(GRID)), ticktext=axis_labels, tickfont=dict(size=8), showgrid=False),
        yaxis=dict(tickvals=list(range(GRID)), ticktext=axis_labels, tickfont=dict(size=8), showgrid=False, autorange="reversed"),
    )
    st.plotly_chart(fig_um, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<p style="font-size:10px;color:#a0a1b0;margin:0;">Dark = cluster boundary · Light = cluster centre</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with rc2:
    st.markdown('<div class="cw-card">', unsafe_allow_html=True)
    st.markdown('<p class="cw-card-title">Churn Rate per SOM Cell</p>', unsafe_allow_html=True)
    fig_ch = go.Figure(go.Heatmap(
        z=churn_mat,
        colorscale=[[0,"#edf7f0"],[0.35,"#a8d4b0"],[0.6,"#e8b84a"],[0.8,"#d47040"],[1,"#b84038"]],
        zmin=0, zmax=1,
        colorbar=dict(thickness=8, len=0.8, tickvals=[0,0.3,0.6,0.8,1], ticktext=["0%","30%","60%","80%","100%"], tickfont=dict(size=8)),
        hovertemplate="Cell (%{x},%{y})<br>Churn Rate: %{z:.0%}<extra></extra>",
    ))
    fig_ch.update_layout(
        **BASE, height=205,
        xaxis=dict(tickvals=list(range(GRID)), ticktext=axis_labels, tickfont=dict(size=8), showgrid=False),
        yaxis=dict(tickvals=list(range(GRID)), ticktext=axis_labels, tickfont=dict(size=8), showgrid=False, autorange="reversed"),
    )
    st.plotly_chart(fig_ch, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<p style="font-size:10px;color:#a0a1b0;margin:0;">Red = high churn risk · Green = low churn risk</p>', unsafe_allow_html=True)
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
            marker=dict(color=color, size=[8 + p/15 for p in p_b], opacity=0.85, line=dict(color="white", width=1)),
            text=[f"{n}<br>{band} — {p}%" for n, p in zip(n_b, p_b)],
            hovertemplate="%{text}<extra></extra>",
        ))
    fig_sc.update_layout(
        **BASE, height=205,
        xaxis=dict(title="SOM Column", range=[-0.3,8.0], showgrid=True, gridcolor="#f0f1f8", tickfont=dict(size=8)),
        yaxis=dict(title="SOM Row",    range=[-0.3,8.0], showgrid=True, gridcolor="#f0f1f8", tickfont=dict(size=8)),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(size=9)),
    )
    st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<p style="font-size:10px;color:#a0a1b0;margin:0;">Marker size proportional to churn probability</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)

# ── ROW 2 — Churn Analysis ─────────────────────────────────────────────────────
st.markdown('<p class="cw-section-label">Churn Analysis</p>', unsafe_allow_html=True)
ra1, ra2, ra3 = st.columns(3)

with ra1:
    st.markdown('<div class="cw-card">', unsafe_allow_html=True)
    st.markdown('<p class="cw-card-title">Churn rate by province</p>', unsafe_allow_html=True)
    prov_df = pd.DataFrame({
        "Province":   ["Limpopo","Mpumalanga","W. Cape","Gauteng","Free State","N. Cape"],
        "Rate":       [73,61,56,40,40,9],
        "Color":      ["#c06858","#c09058","#c09058","#6a8fcb","#6a8fcb","#5a9a6a"],
    })
    fig_pv = go.Figure(go.Bar(
        x=prov_df["Rate"], y=prov_df["Province"], orientation="h",
        marker_color=prov_df["Color"],
        text=prov_df["Rate"].apply(lambda v: f"{v}%"),
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x}%<extra></extra>",
    ))
    fig_pv.update_layout(**BASE, height=210,
        xaxis=dict(visible=False, range=[0,92]),
        yaxis=dict(tickfont=dict(size=10, color="#6b6c80")), bargap=0.38)
    st.plotly_chart(fig_pv, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with ra2:
    st.markdown('<div class="cw-card">', unsafe_allow_html=True)
    st.markdown('<p class="cw-card-title">Risk band distribution</p>', unsafe_allow_html=True)
    fig_rng = go.Figure(go.Pie(
        labels=["Critical","High","Medium","Low"], values=[17,25,25,33],
        hole=0.60, marker_colors=["#c06858","#c09058","#6a8fcb","#5a9a6a"],
        textinfo="label+percent", textfont=dict(size=10),
        hovertemplate="<b>%{label}</b>: %{percent}<extra></extra>",
    ))
    fig_rng.add_annotation(text="<b>2,847</b>", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#1e1f2e"))
    fig_rng.update_layout(**BASE, height=210, showlegend=False)
    st.plotly_chart(fig_rng, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with ra3:
    st.markdown('<div class="cw-card">', unsafe_allow_html=True)
    st.markdown('<p class="cw-card-title">Avg churn score by segment</p>', unsafe_allow_html=True)
    seg_df = pd.DataFrame({"Segment":["Mass","Mid","Affluent"], "Score":[72,51,38], "Color":["#c06858","#c09058","#6a8fcb"]})
    fig_sg = go.Figure(go.Bar(
        x=seg_df["Segment"], y=seg_df["Score"],
        marker_color=seg_df["Color"], marker_cornerradius=4,
        text=seg_df["Score"].apply(lambda v: f"{v}%"),
        textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y}%<extra></extra>",
    ))
    fig_sg.update_layout(**BASE, height=210,
        xaxis=dict(tickfont=dict(size=11, color="#6b6c80"), showgrid=False),
        yaxis=dict(visible=False, range=[0,90]), bargap=0.45)
    st.plotly_chart(fig_sg, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)

# ── ROW 3 — Monthly Trend ──────────────────────────────────────────────────────
st.markdown('<p class="cw-section-label">Monthly Trend</p>', unsafe_allow_html=True)
trend_df = pd.DataFrame({
    "Month": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    "Score": [32,35,31,38,42,46,44,48,51,47,43,46],
})
fig_tr = go.Figure()
fig_tr.add_trace(go.Scatter(
    x=trend_df["Month"], y=trend_df["Score"],
    mode="lines+markers",
    line=dict(color="#4d8a7e", width=2.5),
    marker=dict(color="#4d8a7e", size=5, line=dict(color="white", width=1.5)),
    fill="tozeroy", fillcolor="rgba(77,138,126,0.06)",
    hovertemplate="%{x}: %{y}%<extra></extra>",
))
fig_tr.add_hline(y=trend_df["Score"].mean(), line=dict(dash="dot", color="#c0c1d0", width=1),
    annotation_text=f"  avg {round(trend_df['Score'].mean())}%", annotation_font=dict(size=9, color="#a0a1b0"))
fig_tr.update_layout(**BASE, height=155,
    xaxis=dict(tickfont=dict(size=10, color="#a0a1b0"), showgrid=False),
    yaxis=dict(tickfont=dict(size=10, color="#a0a1b0"), ticksuffix="%", gridcolor="#f4f5fa", range=[0,62], zeroline=False),
    showlegend=False)
st.markdown('<div class="cw-card">', unsafe_allow_html=True)
st.markdown('<p class="cw-card-title">Average churn probability trend — 2025/2026</p>', unsafe_allow_html=True)
st.plotly_chart(fig_tr, use_container_width=True, config={"displayModeBar": False})
st.markdown("</div>", unsafe_allow_html=True)
