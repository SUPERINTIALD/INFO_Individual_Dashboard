import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="CA vs CO Housing Affordability",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# CSS: white app, black text, light blue sidebar
# -----------------------------
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], .stApp {
    background: #ffffff !important;
    color: #111111 !important;
}
[data-testid="stHeader"] {
    background: #ffffff !important;
}
[data-testid="stSidebar"] {
    background: #eaf4ff !important;
}
[data-testid="stSidebar"] * {
    color: #111111 !important;
}
.block-container {
    max-width: 1100px;
    padding-top: 1.4rem;
    padding-bottom: 2rem;
}
.kpi-card {
    background: #fafafa;
    border: 1px solid #dddddd;
    border-radius: 14px;
    padding: 16px 18px 14px 18px;
    min-height: 118px;
}
.kpi-label {
    font-size: 0.92rem;
    color: #666666;
    margin-bottom: 14px;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #111111;
    line-height: 1.1;
}
.kpi-sub {
    margin-top: 10px;
    font-size: 0.82rem;
    color: #888888;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Load data
# -----------------------------
DATA_DIR = Path("./data_Housing")
FOCUS_TIDY = DATA_DIR / "ca_co_us_focus_tidy.csv"

@st.cache_data
def load_data():
    focus = pd.read_csv(FOCUS_TIDY, parse_dates=["date"])
    return focus

focus = load_data()

# keep only CA, CO, and U.S.
focus = focus[
    ((focus["RegionType"] == "msa") & (focus["StateName"].isin(["CA", "CO"]))) |
    (focus["RegionName"] == "United States")
].copy()

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Dashboard controls")

available_dates = sorted(focus["date"].dropna().unique())
snapshot_date = st.sidebar.select_slider(
    "Snapshot date",
    options=available_dates,
    value=available_dates[-1],
    format_func=lambda x: pd.Timestamp(x).strftime("%Y-%m")
)

top_n = st.sidebar.slider(
    "Top metros shown in Chart 1",
    min_value=8,
    max_value=25,
    value=15,
    step=1
)

trend_start_year = st.sidebar.selectbox(
    "Trend chart start year",
    options=[2015, 2016, 2017, 2018, 2019, 2020],
    index=0
)

show_data = st.sidebar.checkbox("Show raw metro table", value=False)

snapshot_date = pd.Timestamp(snapshot_date)
snapshot_label = snapshot_date.strftime("%Y-%m")

# -----------------------------
# Snapshot + trend data
# -----------------------------
latest = focus[focus["date"] == snapshot_date].copy()
us_latest = latest[latest["RegionName"] == "United States"].iloc[0]
metros_latest = latest[latest["RegionType"] == "msa"].copy()

state_latest_summary = (
    metros_latest.groupby("StateName")[["zhvi", "zori", "homeowner_affordability", "renter_affordability"]]
    .median()
    .reset_index()
)

ca_row = state_latest_summary[state_latest_summary["StateName"] == "CA"].iloc[0]
co_row = state_latest_summary[state_latest_summary["StateName"] == "CO"].iloc[0]

state_trends = (
    focus[focus["RegionType"] == "msa"]
    .groupby(["StateName", "date"])[["homeowner_affordability", "zhvi", "zori", "renter_affordability"]]
    .median()
    .reset_index()
)

us_trend = focus[focus["RegionName"] == "United States"].copy()
us_trend = us_trend[us_trend["date"].dt.year >= trend_start_year].copy()
state_trends = state_trends[state_trends["date"].dt.year >= trend_start_year].copy()

# -----------------------------
# Header
# -----------------------------
st.title("California vs. Colorado Housing Affordability")
st.caption("Metro-level Zillow affordability data, with the U.S. as benchmark.")

# -----------------------------
# KPI cards
# -----------------------------
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">U.S. median homeowner burden</div>
        <div class="kpi-value">{us_latest['homeowner_affordability']:.1f}%</div>
        <div class="kpi-sub">National benchmark</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">California median metro burden</div>
        <div class="kpi-value">{ca_row['homeowner_affordability']:.1f}%</div>
        <div class="kpi-sub">Latest metro median</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Colorado median metro burden</div>
        <div class="kpi-value">{co_row['homeowner_affordability']:.1f}%</div>
        <div class="kpi-sub">Latest metro median</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">California premium vs Colorado</div>
        <div class="kpi-value">{(ca_row['homeowner_affordability'] - co_row['homeowner_affordability']):.1f} pts</div>
        <div class="kpi-sub">Difference in burden</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
# =============================
# CHART 1: 1:1 JUPYTER REPLICATION
# =============================
st.subheader(f"1. Housing Burden: Most Expensive CA & CO Metros — {snapshot_label}")

# 1. Prepare data (Match Jupyter's concatenation order)
# plot_df is top metros, sorted so the highest burden is the LAST row (top of chart)
plot_df = (
    metros_latest.dropna(subset=["homeowner_affordability"])
    .sort_values("homeowner_affordability", ascending=True) # Ascending means top burden is at the end
    .tail(top_n)
    .copy()
)

spacer = pd.DataFrame({"RegionName": [" "], "homeowner_affordability": [0], "StateName": ["Spacer"]})
us_row = pd.DataFrame({"RegionName": ["UNITED STATES (AVG)"], "homeowner_affordability": [us_latest["homeowner_affordability"]], "StateName": ["US"]})

# Final order: US at index 0 (bottom), then Spacer, then Metros (highest at top)
final_plot_df = pd.concat([us_row, spacer, plot_df], ignore_index=True)

# 2. Colors and Direct Labels
focus_metros = ["Boulder, CO", "Santa Cruz, CA"]
top_3_names = plot_df.tail(3)["RegionName"].tolist()

colors = []
text_vals = []
label_colors = []

for _, row in final_plot_df.iterrows():
    # BAR COLORS
    if row["RegionName"] in focus_metros:
        colors.append("#ff7f0e" if "CO" in row["RegionName"] else "#1f77b4")
    elif row["StateName"] == "Spacer": colors.append("rgba(0,0,0,0)")
    elif row["StateName"] == "US": colors.append("#edc7c7")
    else: colors.append("#e0e0e0")

    # TEXT LABEL COLORS
    val = row['homeowner_affordability']
    if row["StateName"] == "US":
        text_vals.append(f"U.S. AVG: {val:.1f}%")
        label_colors.append("#c44e52")
    elif row["RegionName"] in focus_metros:
        text_vals.append(f"{val:.1f}%")
        label_colors.append("black")
    elif row["RegionName"] in top_3_names:
        text_vals.append(f"{val:.1f}%")
        label_colors.append("#757575")
    else:
        text_vals.append("")
        label_colors.append("black")

fig1 = go.Figure()

fig1.add_trace(go.Bar(
    x=final_plot_df["homeowner_affordability"],
    y=final_plot_df["RegionName"],
    orientation="h",
    marker=dict(color=colors),
    text=text_vals,
    textposition="outside",
    textfont=dict(color=label_colors, size=12, family="Arial Black"),
    cliponaxis=False
))

# 3. THRESHOLD & SAFE ZONE (Header Logic)
threshold = 30

# Vertical Dashed Line (Goes through all bars)
fig1.add_shape(
    type="line", x0=threshold, x1=threshold, y0=0, y1=1,
    xref="x", yref="paper",
    line=dict(color="#2e7d32", width=1.5, dash="dash")
)

# Header Safe Zone Box (Sitting ABOVE the bars)
# y0=1.005 starts it just above the plotting area
fig1.add_shape(
    type="rect", x0=0, x1=threshold, y0=1.01, y1=1.05,
    xref="x", yref="paper",
    fillcolor="rgba(0,128,0,0.12)", line=dict(width=0)
)

# Annotations (Positioned in the margin)
fig1.add_annotation(
    x=threshold/2, y=1.05, xref="x", yref="paper",
    text="SAFE ZONE", showarrow=False,
    font=dict(size=10, color="#2e7d32", family="Arial Black")
)

fig1.add_annotation(
    x=threshold, y=1.02, xref="x", yref="paper",
    text=" 30% AFFORDABILITY THRESHOLD", showarrow=False,
    xanchor="left", yanchor="bottom",
    font=dict(size=10, color="#2e7d32", family="Arial Black")
)

# 4. LAYOUT & POLISH (No Borders, Proper Spacing)
fig1.update_layout(
    title=dict(
        text=
             "<span style='font-size:14px; color:#555555; font-weight:normal;'>"
             "California fills nearly all highest-burden slots; Boulder is the lone Colorado metro breaking into this group.</span>",
        x=0, xanchor='left', font=dict(size=24, color="black")
    ),
    height=800,
    # Increased top margin (t=160) to provide room for the safe zone header
    margin=dict(l=180, r=80, t=160, b=80),
    paper_bgcolor="white",
    plot_bgcolor="white",
    showlegend=False,
    xaxis=dict(
        title="Homeowner affordability (% of median household income)",
        title_font=dict(color="#555555", size=13),
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        showline=False, # No bottom spine
        range=[0, float(final_plot_df["homeowner_affordability"].max()) + 15]
    ),
    yaxis=dict(
        tickfont=dict(color="black", size=12),
        showgrid=False,
        zeroline=False,
        showline=False # No left spine
    )
)

st.plotly_chart(fig1, use_container_width=True, theme=None)

st.markdown("---")

# =============================
# CHART 2
# =============================
st.subheader(f"2. Homeowner Affordability Over Time — since {trend_start_year}")

fig2 = go.Figure()

for state, color, label in [
    ("CA", "#1f77b4", "CA Median Line"),
    ("CO", "#ff7f0e", "CO Median Line"),
]:
    tmp = state_trends[state_trends["StateName"] == state]
    fig2.add_trace(go.Scatter(
        x=tmp["date"],
        y=tmp["homeowner_affordability"],
        mode="lines",
        name=label,
        line=dict(color=color, width=2.5),
        hovertemplate=f"<b>{label}</b><br>%{{x|%Y-%m}}<br>%{{y:.1f}}%<extra></extra>"
    ))

    if not tmp.empty:
        fig2.add_annotation(
            x=tmp["date"].iloc[-1],
            y=tmp["homeowner_affordability"].iloc[-1],
            text=label,
            showarrow=False,
            xanchor="left",
            xshift=8,
            font=dict(size=11, color=color)
        )

fig2.add_trace(go.Scatter(
    x=us_trend["date"],
    y=us_trend["homeowner_affordability"],
    mode="lines",
    name="U.S. Average Line",
    line=dict(color="gray", width=2, dash="dash"),
    hovertemplate="<b>U.S. Average</b><br>%{x|%Y-%m}<br>%{y:.1f}%<extra></extra>"
))

if not us_trend.empty:
    fig2.add_annotation(
        x=us_trend["date"].iloc[-1],
        y=us_trend["homeowner_affordability"].iloc[-1],
        text="U.S. Average Line",
        showarrow=False,
        xanchor="left",
        xshift=8,
        font=dict(size=11, color="gray")
    )

# 30% affordability threshold
fig2.add_shape(
    type="line",
    x0=us_trend["date"].min(),
    x1=us_trend["date"].max(),
    y0=30, y1=30,
    xref="x", yref="y",
    line=dict(color="#7d7b7a", width=1.5, dash="dot")
)

fig2.add_annotation(
    x=us_trend["date"].min(),
    y=30,
    text="30% Affordability Threshold",
    showarrow=False,
    xanchor="left",
    yshift=8,
    font=dict(size=9, color="#7d7b7a")
)
fig2.update_layout(
    title=dict(
        text=
             "<sup>Values represent the median across all metros in each state.</sup>",
        x=0,
        xanchor='left',
        font=dict(size=18, color="black")
    ),
    margin=dict(l=60, r=120, t=100, b=50),
    paper_bgcolor="white",
    plot_bgcolor="white",
    xaxis=dict(
        title="Date",
        color="black",
        showgrid=False,
        showline=True,
        linecolor='black'
    ),
    yaxis=dict(
        title="Homeowner affordability (%)",
        color="black",
        showgrid=True,
        gridcolor="#eeeeee", # Very faint grid
        showline=True,
        linecolor='black'
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        font=dict(color="black")
    )
)

st.plotly_chart(fig2, use_container_width=True, theme=None)
st.markdown("---")

# =============================
# CHART 3
# =============================
st.subheader(f"3. The Buying Premium — {snapshot_label}")

summary = pd.DataFrame({
    "Group": ["United States", "California", "Colorado"],
    "Homeowner": [
        us_latest["homeowner_affordability"],
        state_latest_summary.loc[state_latest_summary["StateName"] == "CA", "homeowner_affordability"].iloc[0],
        state_latest_summary.loc[state_latest_summary["StateName"] == "CO", "homeowner_affordability"].iloc[0],
    ],
    "Renter": [
        us_latest["renter_affordability"],
        state_latest_summary.loc[state_latest_summary["StateName"] == "CA", "renter_affordability"].iloc[0],
        state_latest_summary.loc[state_latest_summary["StateName"] == "CO", "renter_affordability"].iloc[0],
    ]
})
summary["Gap"] = summary["Homeowner"] - summary["Renter"]

home_colors = []
rent_colors = []
home_text_colors = []
rent_text_colors = []

for _, row in summary.iterrows():
    if row["Group"] == "California":
        home_colors.append("rgba(31,119,180,1.0)")
        rent_colors.append("rgba(169,204,227,1.0)")
        home_text_colors.append("black")
        rent_text_colors.append("#444444")
    else:
        home_colors.append("rgba(31,119,180,0.3)")
        rent_colors.append("rgba(169,204,227,0.3)")
        home_text_colors.append("rgba(0,0,0,0.45)")
        rent_text_colors.append("rgba(68,68,68,0.45)")

fig3 = go.Figure()

fig3.add_trace(go.Bar(
    x=summary["Group"],
    y=summary["Homeowner"],
    name="Homeowner Burden",
    marker_color=home_colors,
    text=[f"{v:.1f}%" for v in summary["Homeowner"]],
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Homeowner burden: %{y:.1f}%<extra></extra>"
))

fig3.add_trace(go.Bar(
    x=summary["Group"],
    y=summary["Renter"],
    name="Renter Burden",
    marker_color=rent_colors,
    text=[f"{v:.1f}%" for v in summary["Renter"]],
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Renter burden: %{y:.1f}%<extra></extra>"
))

# 30% threshold
fig3.add_shape(
    type="line",
    x0=-0.5, x1=2.5,
    y0=30, y1=30,
    xref="x", yref="y",
    line=dict(color="#8a8a8a", width=1.2, dash="dash")
)

fig3.add_annotation(
    x=2.55,
    y=30,
    text="30% affordability<br>threshold",
    showarrow=False,
    xanchor="left",
    yanchor="middle",
    font=dict(size=8.5, color="#8a8a8a")
)

# California-only gap bracket
ca_idx = 1
ca_home = summary.loc[ca_idx, "Homeowner"]
ca_rent = summary.loc[ca_idx, "Renter"]
ca_gap = summary.loc[ca_idx, "Gap"]

# vertical bracket line
fig3.add_shape(
    type="line",
    x0=ca_idx + 0.32, x1=ca_idx + 0.32,
    y0=ca_rent + 2, y1=ca_home + 2,
    xref="x", yref="y",
    line=dict(color="#1f77b4", width=1.8)
)
# top cap
fig3.add_shape(
    type="line",
    x0=ca_idx + 0.28, x1=ca_idx + 0.32,
    y0=ca_home + 2, y1=ca_home + 2,
    xref="x", yref="y",
    line=dict(color="#1f77b4", width=1.8)
)
# bottom cap
fig3.add_shape(
    type="line",
    x0=ca_idx + 0.28, x1=ca_idx + 0.32,
    y0=ca_rent + 2, y1=ca_rent + 2,
    xref="x", yref="y",
    line=dict(color="#1f77b4", width=1.8)
)

fig3.add_annotation(
    x=ca_idx + 0.43,
    y=(ca_home + ca_rent + 4) / 2,
    text=f"+{ca_gap:.1f} pts",
    showarrow=False,
    font=dict(size=10, color="#1f77b4")
)
fig3.update_traces(textfont=dict(color="black", size=12))

fig3.update_layout(
    title=dict(
        text=
             "<sup>Buying requires a much larger share of income than renting, especially in California.</sup>",
        x=0,
        xanchor='left',
        font=dict(size=18, color="black")
    ),
    margin=dict(l=20, r=80, t=100, b=50),
    barmode="group",
    paper_bgcolor="white",
    plot_bgcolor="white",
    xaxis=dict(
        showline=True,
        linecolor='#cccccc', # Faded bottom spine from your notebook
        tickfont=dict(color="black")
    ),
    yaxis=dict(
        showticklabels=False, # Matches ax.set_yticks([])
        showgrid=False,
        showline=False
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        font=dict(color="black")
    )
)

st.plotly_chart(fig3, use_container_width=True, theme=None)
# -----------------------------
# Optional table
# -----------------------------
if show_data:
    st.markdown("---")
    st.subheader(f"Latest Metro-Level Data — {snapshot_label}")
    st.dataframe(
        metros_latest[[
            "RegionName", "StateName", "zhvi", "zori",
            "homeowner_affordability", "renter_affordability"
        ]].sort_values("homeowner_affordability", ascending=False),
        use_container_width=True
    )



st.markdown("---")
st.markdown(
    """
    <div style="color: #555555; font-size: 0.85rem;">
    <b>Data Sources:</b><br>
    • <b>Housing Prices:</b> Zillow Home Value Index (ZHVI) and Zillow Observed Rent Index (ZORI).<br>
    • <b>Incomes:</b> Median Household Income from the American Community Survey (ACS) 5-Year Estimates.<br>
    • <b>Methodology:</b> Affordability is calculated as the percentage of median gross monthly income required to cover median mortgage payments (assuming 20% down) or median rent.
    </div>
    """, 
    unsafe_allow_html=True
)