"""
SIH Landslide Early Warning System — Phase 10 Interactive Dashboard
====================================================================

Visualization and monitoring layer over Phase 9 prediction outputs.

IMPORTANT — this dashboard NEVER:
  - retrains the ML model
  - modifies model predictions or probabilities
  - regenerates rainfall features
  - fabricates or simulates data (except in the isolated What-If sandbox)

It only reads and displays the three provided Phase 9 output files:
  data/latest_location_risk.csv
  data/all_daily_live_predictions.csv
  data/risk_summary.json
"""

import os
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --- Pipeline Integration for What-If Analysis ---
from generate_predictions import load_artifact, assign_risk_level, MODEL_ARTIFACT_PATH
from config import RAINY_DAY_THRESHOLD_MM, HEAVY_RAIN_DAY_THRESHOLD_MM

# --------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="SIH Landslide Early Warning System",
    page_icon="🌍",
    layout="wide",
)

DATA_DIR = "data"
LATEST_RISK_PATH = os.path.join(DATA_DIR, "latest_location_risk.csv")
ALL_PREDICTIONS_PATH = os.path.join(DATA_DIR, "all_daily_live_predictions.csv")
RISK_SUMMARY_PATH = os.path.join(DATA_DIR, "risk_summary.json")

RISK_ORDER = ["LOW", "MODERATE", "HIGH", "CRITICAL"]
RISK_COLORS = {
    "LOW": "#2ecc71",
    "MODERATE": "#f1c40f",
    "HIGH": "#e67e22",
    "CRITICAL": "#e74c3c",
}

# Any gap between two consecutive dated records for the same location that is
# wider than this (in days) is treated as "not continuous monitoring" and is
# visually broken / shaded in the Historical Trends chart, instead of being
# smoothed over by Plotly's default straight-line interpolation.
TREND_GAP_THRESHOLD_DAYS = 30

REQUIRED_COLUMNS = [
    "location_id", "date", "latitude", "longitude",
    "elevation_m", "slope_deg",
    "rainfall_mm", "rainfall_1d_mm",
    "consecutive_rainy_days", "consecutive_heavy_rain_days",
    "landslide_probability", "probability_percent",
    "operating_threshold", "model_decision", "warning_status",
    "risk_level", "prediction_timestamp_utc",
]


# --------------------------------------------------------------------------
# DATA VALIDATION + LOADING
# --------------------------------------------------------------------------
def validate_files_exist():
    """Check that all three required input files exist. Stop with a clear
    error (not a raw traceback) if any are missing."""
    missing = []
    for label, path in [
        ("Latest Location Risk", LATEST_RISK_PATH),
        ("All Daily Predictions", ALL_PREDICTIONS_PATH),
        ("Risk Summary", RISK_SUMMARY_PATH),
    ]:
        if not os.path.exists(path):
            missing.append(f"- **{label}** expected at `{path}`")

    if missing:
        st.error(
            "### Required Phase 9 input file(s) missing\n\n"
            + "\n".join(missing)
            + "\n\nPlace the missing file(s) in the `data/` folder and reload "
              "the app. The dashboard cannot render without the real Phase 9 "
              "outputs — no dummy or simulated data will be substituted."
        )
        st.stop()


def validate_columns(df: pd.DataFrame, df_label: str):
    """Check required columns are present; show a clear error if not."""
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        st.error(
            f"### `{df_label}` is missing required column(s)\n\n"
            f"Missing: `{', '.join(missing_cols)}`\n\n"
            "The dashboard cannot safely render this data. Please check the "
            "Phase 9 output file and reload the app."
        )
        st.stop()


CACHE_TTL_SECONDS = 900  # 15 min — data/ files are regenerated hourly by generate_predictions.py;
                          # without a TTL, st.cache_data would keep serving the data from the
                          # moment the app started, indefinitely, even after a git push updates
                          # the files on disk.


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Safe date parsing — invalid dates become NaT rather than crashing.
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    numeric_cols = [
        "latitude", "longitude", "elevation_m", "slope_deg",
        "rainfall_mm", "rainfall_1d_mm",
        "consecutive_rainy_days", "consecutive_heavy_rain_days",
        "landslide_probability", "probability_percent",
        "operating_threshold",
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def get_operating_threshold(latest_df: pd.DataFrame, summary: dict) -> float:
    """Load the operating threshold dynamically — prefer risk_summary.json,
    fall back to the CSV data. Never hardcode."""
    if summary and "operating_threshold" in summary and summary["operating_threshold"] is not None:
        return float(summary["operating_threshold"])
    if "operating_threshold" in latest_df.columns and latest_df["operating_threshold"].notna().any():
        return float(latest_df["operating_threshold"].dropna().iloc[0])
    st.warning(
        "Operating threshold not found in risk_summary.json or the CSV data. "
        "Threshold-dependent visuals will be hidden."
    )
    return None


def ordered_risk_counts(df: pd.DataFrame) -> pd.Series:
    counts = df["risk_level"].value_counts()
    return counts.reindex(RISK_ORDER, fill_value=0)


def find_trend_gaps(dates: pd.Series, threshold_days: int = TREND_GAP_THRESHOLD_DAYS):
    """Given a sorted, deduped Series of dates for one location, return a list
    of (gap_start, gap_end) tuples for every consecutive pair whose spacing
    exceeds threshold_days. Used to keep the trend line from silently
    interpolating across long stretches with no real monitoring data
    (e.g. the jump from historical Phase 4 training dates to the first live
    Phase 11 prediction)."""
    gaps = []
    dates = dates.dropna().sort_values().reset_index(drop=True)
    if len(dates) < 2:
        return gaps
    diffs = dates.diff()
    for i in range(1, len(dates)):
        if pd.notna(diffs.iloc[i]) and diffs.iloc[i] > pd.Timedelta(days=threshold_days):
            gaps.append((dates.iloc[i - 1], dates.iloc[i]))
    return gaps


def build_gap_broken_trend(loc_history: pd.DataFrame, threshold_days: int = TREND_GAP_THRESHOLD_DAYS):
    """Return (plot_df, gaps) where plot_df has a None/NaN row inserted at
    every detected gap so Plotly draws a break in the line instead of a
    straight interpolated segment across it. loc_history must already be
    sorted by date and contain 'date' and 'landslide_probability'."""
    working = loc_history[["date", "landslide_probability"]].dropna(subset=["date"]).copy()
    gaps = find_trend_gaps(working["date"], threshold_days=threshold_days)

    if not gaps:
        return working, gaps

    # Insert a break row just after each gap's start date. A None y-value
    # tells Plotly to lift the pen rather than connect the two real points.
    break_rows = pd.DataFrame({
        "date": [gap_start + pd.Timedelta(hours=12) for gap_start, _ in gaps],
        "landslide_probability": [None] * len(gaps),
    })
    plot_df = pd.concat([working, break_rows], ignore_index=True).sort_values("date").reset_index(drop=True)
    return plot_df, gaps


# --------------------------------------------------------------------------
# LOAD DATA
# --------------------------------------------------------------------------
validate_files_exist()

latest_df = load_csv(LATEST_RISK_PATH)
history_df = load_csv(ALL_PREDICTIONS_PATH)
risk_summary = load_json(RISK_SUMMARY_PATH)

validate_columns(latest_df, "latest_location_risk.csv")
validate_columns(history_df, "all_daily_live_predictions.csv")

OPERATING_THRESHOLD = get_operating_threshold(latest_df, risk_summary)

# --------------------------------------------------------------------------
# HEADER
# --------------------------------------------------------------------------
title_col, refresh_col = st.columns([5, 1])
with title_col:
    st.title("🌍 SIH Landslide Early Warning System")
    st.markdown("#### Phase 10 Interactive Dashboard — Powered by Phase 9 Prediction Outputs")
with refresh_col:
    st.write("")  # vertical spacer to align the button with the title
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

model_name = risk_summary.get("model_name", "Random Forest")
header_cols = st.columns(3)
header_cols[0].markdown(f"**Production Model:** {model_name}")
header_cols[1].markdown("**Pipeline:** Historical Replay Prediction Pipeline")
header_cols[2].markdown(
    f"**Operating Threshold:** {OPERATING_THRESHOLD:.2f}" if OPERATING_THRESHOLD is not None else "**Operating Threshold:** N/A"
)

st.markdown(
    "> WARNING / NO_WARNING is the production model's binary decision, based on the "
    "operating threshold above. LOW / MODERATE / HIGH / CRITICAL are dashboard-only "
    "presentation categories and do **not** replace that decision."
)

st.divider()

# --------------------------------------------------------------------------
# TABS / NAVIGATION
# --------------------------------------------------------------------------
tabs = st.tabs([
    "📊 KPI Overview",
    "🗺️ Risk Map",
    "🚨 Warning Center",
    "📍 Location Explorer",
    "📈 Historical Trends",
    "📉 Analytics",
    "ℹ️ System Info",
    "🧪 What-If Analysis"  # NEW TAB ADDED HERE
])

# --------------------------------------------------------------------------
# SECTION 1 — KPI OVERVIEW
# --------------------------------------------------------------------------
with tabs[0]:
    st.subheader("KPI Overview")

    total_locations = risk_summary.get("total_locations", latest_df["location_id"].nunique())
    total_records = risk_summary.get("total_prediction_records", len(history_df))
    warnings_count = risk_summary.get("warnings", int((latest_df["warning_status"] == "WARNING").sum()))
    no_warnings_count = risk_summary.get("no_warnings", int((latest_df["warning_status"] == "NO_WARNING").sum()))
    mean_prob = risk_summary.get("mean_landslide_probability", float(latest_df["landslide_probability"].mean()))
    max_prob = risk_summary.get("max_landslide_probability", float(latest_df["landslide_probability"].max()))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Monitored Locations", f"{total_locations:,}")
    c2.metric("Total Prediction Records", f"{total_records:,}")
    c3.metric("Warning Locations", f"{warnings_count:,}")
    c4.metric("No-Warning Locations", f"{no_warnings_count:,}")

    c5, c6, c7 = st.columns(3)
    c5.metric("Mean Landslide Probability", f"{mean_prob:.3f}")
    c6.metric("Maximum Landslide Probability", f"{max_prob:.3f}")
    c7.metric("Operating Threshold", f"{OPERATING_THRESHOLD:.2f}" if OPERATING_THRESHOLD is not None else "N/A")

    st.caption(
        "KPI values are sourced from risk_summary.json where available, with a "
        "fallback calculation from the latest_location_risk.csv data. Original "
        "model output is never modified."
    )

# --------------------------------------------------------------------------
# SECTION 2 — INTERACTIVE RISK MAP
# --------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Interactive Risk Map")

    map_filter_cols = st.columns(3)
    with map_filter_cols[0]:
        risk_filter = st.multiselect(
            "Risk level", RISK_ORDER, default=RISK_ORDER, key="map_risk_filter"
        )
    with map_filter_cols[1]:
        warning_filter = st.selectbox(
            "Warning status", ["ALL", "WARNING", "NO_WARNING"], key="map_warning_filter"
        )
    with map_filter_cols[2]:
        min_prob = st.slider(
            "Minimum probability", 0.0, 1.0, 0.0, 0.01, key="map_min_prob"
        )

    map_df = latest_df[latest_df["risk_level"].isin(risk_filter)]
    if warning_filter != "ALL":
        map_df = map_df[map_df["warning_status"] == warning_filter]
    map_df = map_df[map_df["landslide_probability"] >= min_prob]

    st.caption(f"Showing {len(map_df):,} of {len(latest_df):,} locations")

    if len(map_df) == 0:
        st.info("No locations match the current filters.")
    else:
        fig_map = px.scatter_mapbox(
            map_df,
            lat="latitude",
            lon="longitude",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
            category_orders={"risk_level": RISK_ORDER},
            size="probability_percent",
            size_max=18,
            hover_data={
                "location_id": True,
                "date": True,
                "landslide_probability": ":.3f",
                "probability_percent": ":.2f",
                "risk_level": True,
                "warning_status": True,
                "elevation_m": ":.1f",
                "slope_deg": ":.2f",
                "rainfall_mm": ":.2f",
                "rainfall_1d_mm": ":.2f",
                "latitude": False,
                "longitude": False,
            },
            zoom=9,
            height=600,
        )
        
       # Apply free Esri satellite imagery + Location Labels (Hybrid View)
        fig_map.update_layout(
            mapbox_style="white-bg",
            mapbox_layers=[
                # Base Layer: Satellite Imagery
                {
                    "below": 'traces',
                    "sourcetype": "raster",
                    "sourceattribution": "Esri Satellite",
                    "source": [
                        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    ]
                },
                # Overlay Layer: Location Names & Boundaries
                {
                    "below": 'traces',
                    "sourcetype": "raster",
                    "sourceattribution": "Esri Labels",
                    "source": [
                        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                    ]
                }
            ],
            margin=dict(l=0, r=0, t=0, b=0)
        )

# --------------------------------------------------------------------------
# SECTION 3 — WARNING CENTER
# --------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Warning Center")

    warning_df = latest_df[latest_df["warning_status"] == "WARNING"].copy()
    high_df = latest_df[latest_df["risk_level"] == "HIGH"]
    critical_df = latest_df[latest_df["risk_level"] == "CRITICAL"]

    w1, w2, w3 = st.columns(3)
    w1.metric("Total Warning Locations", f"{len(warning_df):,}")
    w2.metric("HIGH Risk Locations", f"{len(high_df):,}")
    w3.metric("CRITICAL Risk Locations", f"{len(critical_df):,}")

    warning_display_cols = [
        "location_id", "date", "probability_percent", "risk_level",
        "warning_status", "rainfall_mm", "rainfall_1d_mm",
        "consecutive_rainy_days", "consecutive_heavy_rain_days",
        "elevation_m", "slope_deg",
    ]
    warning_table = warning_df.sort_values("landslide_probability", ascending=False)[warning_display_cols]

    st.dataframe(warning_table, use_container_width=True, height=400)

    st.download_button(
        label="⬇️ Download Warning Locations CSV",
        data=warning_table.to_csv(index=False).encode("utf-8"),
        file_name="phase10_warning_locations.csv",
        mime="text/csv",
    )

# --------------------------------------------------------------------------
# SECTION 4 — LOCATION RISK EXPLORER
# --------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Location Risk Explorer")

    location_ids = sorted(latest_df["location_id"].unique())
    selected_location = st.selectbox("Select a location_id", location_ids, key="explorer_location")

    loc_row = latest_df[latest_df["location_id"] == selected_location].iloc[0]

    st.markdown("### Risk Information")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Landslide Probability", f"{loc_row['landslide_probability']:.3f}")
    r2.metric("Probability Percent", f"{loc_row['probability_percent']:.2f}%")
    r3.metric("Risk Level", loc_row["risk_level"])
    r4.metric("Warning Status", loc_row["warning_status"])

    r5, r6 = st.columns(2)
    r5.metric("Model Decision", "1 (Positive)" if loc_row["model_decision"] == 1 else "0 (Negative)")
    date_val = loc_row["date"]
    r6.metric("Prediction Date", date_val.strftime("%Y-%m-%d") if pd.notna(date_val) else "N/A")

    st.markdown("### Terrain Information")
    t1, t2 = st.columns(2)
    t1.metric("Elevation (m)", f"{loc_row['elevation_m']:.1f}")
    t2.metric("Slope (deg)", f"{loc_row['slope_deg']:.2f}")

    st.markdown("### Rainfall Information")
    rf1, rf2, rf3, rf4 = st.columns(4)
    rf1.metric("Rainfall (mm)", f"{loc_row['rainfall_mm']:.2f}")
    rf2.metric("1-Day Rainfall (mm)", f"{loc_row['rainfall_1d_mm']:.2f}")
    rf3.metric("Consecutive Rainy Days", f"{loc_row['consecutive_rainy_days']:.0f}")
    rf4.metric("Consecutive Heavy Rain Days", f"{loc_row['consecutive_heavy_rain_days']:.0f}")

    st.markdown("### Model Decision Explanation")
    threshold_str = f"{OPERATING_THRESHOLD:.2f}" if OPERATING_THRESHOLD is not None else "N/A"
    st.info(
        f"The production operating threshold is **{threshold_str}**. "
        f"The predicted probability for location **{selected_location}** is "
        f"**{loc_row['landslide_probability']:.3f}**, which results in a "
        f"**{loc_row['warning_status']}** decision from the production model.\n\n"
        f"Separately, the dashboard assigns this location a **{loc_row['risk_level']}** "
        f"presentation category, based on fixed display bands. "
        f"**WARNING/NO_WARNING is the production model decision** — the risk "
        f"category is for dashboard presentation only and does not replace it."
    )

# --------------------------------------------------------------------------
# SECTION 5 — HISTORICAL RISK TRENDS
# --------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Historical Risk Trends")

    trend_locations = sorted(history_df["location_id"].unique())
    default_idx = trend_locations.index(selected_location) if selected_location in trend_locations else 0
    trend_location = st.selectbox(
        "Select a location_id", trend_locations, index=default_idx, key="trend_location"
    )

    loc_history = history_df[history_df["location_id"] == trend_location].sort_values("date")

    if len(loc_history) == 0:
        st.info("No historical records found for this location.")
    else:
        # Break the line across any gap wider than TREND_GAP_THRESHOLD_DAYS so
        # Plotly doesn't draw a misleading straight-line interpolation between,
        # e.g., historical Phase 4 training dates and the first live Phase 11
        # prediction. See build_gap_broken_trend() / find_trend_gaps() above.
        plot_df, gaps = build_gap_broken_trend(loc_history, TREND_GAP_THRESHOLD_DAYS)

        if gaps:
            gap_word = "gap" if len(gaps) == 1 else "gaps"
            st.warning(
                f"⚠️ This location has {len(gaps)} data {gap_word} of more than "
                f"{TREND_GAP_THRESHOLD_DAYS} days with no recorded predictions "
                "(shaded below). The line is broken across each gap so it isn't "
                "mistaken for continuous monitoring — it most likely reflects the "
                "jump from historical replay data to live daily predictions."
            )

        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Scatter(
                x=plot_df["date"],
                y=plot_df["landslide_probability"],
                mode="lines+markers",
                name="Landslide Probability",
                line=dict(color="#3498db"),
                connectgaps=False,  # respect the None rows inserted at gaps
            )
        )

        # Shade each detected gap region so it's visually obvious even before
        # reading the warning text above.
        for gap_start, gap_end in gaps:
            fig_trend.add_vrect(
                x0=gap_start,
                x1=gap_end,
                fillcolor="gray",
                opacity=0.15,
                line_width=0,
                annotation_text="no data",
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color="gray",
            )

        if OPERATING_THRESHOLD is not None:
            fig_trend.add_hline(
                y=OPERATING_THRESHOLD,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Operating Threshold ({OPERATING_THRESHOLD:.2f})",
                annotation_position="top left",
            )
        fig_trend.update_yaxes(range=[0, 1], title="Landslide Probability")
        fig_trend.update_xaxes(title="Date")
        fig_trend.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("#### Historical Data")
        hist_display_cols = [
            "date", "probability_percent", "risk_level", "warning_status",
            "rainfall_mm", "rainfall_1d_mm",
        ]
        hist_table = loc_history[hist_display_cols].copy()
        hist_table["date"] = hist_table["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(hist_table, use_container_width=True, height=350)

# --------------------------------------------------------------------------
# SECTION 6 — ANALYTICS
# --------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Analytics")

    st.markdown("#### Risk Distribution")
    risk_counts = ordered_risk_counts(latest_df)
    fig_risk_dist = px.bar(
        x=risk_counts.index,
        y=risk_counts.values,
        color=risk_counts.index,
        color_discrete_map=RISK_COLORS,
        category_orders={"x": RISK_ORDER},
        labels={"x": "Risk Level", "y": "Count"},
    )
    fig_risk_dist.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_risk_dist, use_container_width=True)

    st.markdown("#### Probability Distribution")
    fig_hist = px.histogram(
        latest_df,
        x="landslide_probability",
        nbins=30,
        labels={"landslide_probability": "Landslide Probability"},
    )
    if OPERATING_THRESHOLD is not None:
        fig_hist.add_vline(
            x=OPERATING_THRESHOLD,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Threshold ({OPERATING_THRESHOLD:.2f})",
            annotation_position="top right",
        )
    fig_hist.update_layout(height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("#### Rainfall vs Probability")
    fig_scatter = px.scatter(
        latest_df,
        x="rainfall_mm",
        y="landslide_probability",
        color="risk_level",
        color_discrete_map=RISK_COLORS,
        category_orders={"risk_level": RISK_ORDER},
        hover_data=["location_id"],
        labels={"rainfall_mm": "Rainfall (mm)", "landslide_probability": "Landslide Probability"},
    )
    fig_scatter.update_layout(height=450)
    st.plotly_chart(fig_scatter, use_container_width=True)

# --------------------------------------------------------------------------
# SECTION 7 — SYSTEM INFORMATION
# --------------------------------------------------------------------------
with tabs[6]:
    st.subheader("System Information")

    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f"**Model Name:** {model_name}")
        st.markdown(f"**Operating Threshold:** {OPERATING_THRESHOLD:.2f}" if OPERATING_THRESHOLD is not None else "**Operating Threshold:** N/A")
        st.markdown(f"**Total Monitored Locations:** {total_locations:,}")
    with s2:
        st.markdown(f"**Total Prediction Records:** {total_records:,}")
        st.markdown(f"**Prediction Timestamp:** {risk_summary.get('prediction_timestamp_utc', 'N/A')}")
        st.markdown(f"**Phase:** {risk_summary.get('phase', 9)}")

    st.markdown("#### Pipeline")
    st.code(
        "Terrain + Rainfall Data\n"
        "        ↓\n"
        "Feature Engineering\n"
        "        ↓\n"
        "ML Dataset\n"
        "        ↓\n"
        "Model Training and Evaluation\n"
        "        ↓\n"
        "Production Random Forest\n"
        "        ↓\n"
        "Phase 9 Prediction Pipeline\n"
        "        ↓\n"
        "Phase 10 Interactive Dashboard",
        language=None,
    )

# --------------------------------------------------------------------------
# SECTION 8 — WHAT-IF ANALYSIS (NEW)
# --------------------------------------------------------------------------
with tabs[7]:
    st.subheader("🧪 What-If Landslide Prediction")
    st.markdown("Test manual scenarios or stress-test the entire map against the trained model.")

    # Load the model exactly as the pipeline does
    try:
        artifact = load_artifact(MODEL_ARTIFACT_PATH)
        model = artifact["model"]
        features_list = artifact["features"]
        artifact_threshold = artifact["operating_threshold"]
    except Exception as e:
        st.error(f"Could not load model artifact: {e}")
        st.stop()

    sim_mode = st.radio(
        "Select Simulation Mode:", 
        ["📍 Single Location Check", "🗺️ Global Map Scenario"], 
        horizontal=True
    )
    st.divider()

    if sim_mode == "📍 Single Location Check":
        # Location Pre-fill System
        st.markdown("#### Input Parameters")
        use_existing = st.checkbox("Pre-fill terrain from an existing location", value=False)
        
        default_elev = 500.0
        default_slope = 25.0
        
        if use_existing:
            whatif_locs = sorted(latest_df["location_id"].unique())
            chosen_loc = st.selectbox("Select Location to Pre-fill", whatif_locs)
            loc_data = latest_df[latest_df["location_id"] == chosen_loc].iloc[0]
            default_elev = float(loc_data["elevation_m"])
            default_slope = float(loc_data["slope_deg"])
            st.info(f"Loaded terrain values for {chosen_loc}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Terrain Features**")
            elevation = st.number_input("Elevation (m)", min_value=0.0, value=default_elev, step=10.0)
            slope = st.number_input("Slope (degrees)", min_value=0.0, max_value=90.0, value=default_slope, step=1.0)

        with col2:
            st.markdown("**Rainfall Features**")
            st.caption(f"Thresholds: Rainy day ≥ {RAINY_DAY_THRESHOLD_MM}mm | Heavy rain ≥ {HEAVY_RAIN_DAY_THRESHOLD_MM}mm")
            
            rainfall_today = st.number_input("Today's Rainfall (mm)", min_value=0.0, value=0.0, step=1.0)
            consecutive_rainy = st.number_input("Consecutive Rainy Days (Ending Today)", min_value=0, value=0, step=1)
            consecutive_heavy = st.number_input("Consecutive Heavy Rain Days (Ending Today)", min_value=0, value=0, step=1)

        if st.button("Generate Prediction", type="primary", key="whatif_single_btn"):
            input_data = {
                "elevation_m": elevation,
                "slope_deg": slope,
                "rainfall_mm": rainfall_today,
                "rainfall_1d_mm": rainfall_today, 
                "consecutive_rainy_days": consecutive_rainy,
                "consecutive_heavy_rain_days": consecutive_heavy
            }
            
            missing_feats = [f for f in features_list if f not in input_data]
            if missing_feats:
                st.error(f"Missing input for required features: {missing_feats}")
            else:
                df_input = pd.DataFrame([input_data])[features_list]
                
                probability = model.predict_proba(df_input)[:, 1][0]
                risk_label = assign_risk_level(probability)
                is_warning = probability >= artifact_threshold
                
                st.divider()
                st.subheader("Prediction Results")
                
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                metric_col1.metric("Landslide Probability", f"{probability * 100:.1f}%", f"{probability:.3f} raw")
                metric_col2.metric("Risk Level", risk_label)
                metric_col3.metric(
                    "System Action", 
                    "🚨 WARNING" if is_warning else "✅ NO WARNING",
                    delta="Over Threshold" if is_warning else "Safe",
                    delta_color="inverse" if is_warning else "normal"
                )

    else:
        st.markdown("#### Global Rainfall Scenario")
        st.markdown(
            "Apply a single hypothetical rainfall scenario to **all monitored locations** "
            "to see which terrains would trigger a warning under these conditions."
        )

        sim_col1, sim_col2, sim_col3 = st.columns(3)
        sim_rainfall = sim_col1.number_input("Simulated Today's Rainfall (mm)", min_value=0.0, value=60.0, step=10.0)
        sim_rainy = sim_col2.number_input("Simulated Consecutive Rainy Days", min_value=0, value=3, step=1)
        sim_heavy = sim_col3.number_input("Simulated Consecutive Heavy Rain Days", min_value=0, value=1, step=1)

        if st.button("Simulate Map Risk", type="primary", key="whatif_map_btn"):
            # Extract real terrain data for all locations
            sim_df = latest_df[['location_id', 'latitude', 'longitude', 'elevation_m', 'slope_deg']].copy()
            
            # Inject the hypothetical rainfall universally
            sim_df['rainfall_mm'] = sim_rainfall
            sim_df['rainfall_1d_mm'] = sim_rainfall
            sim_df['consecutive_rainy_days'] = sim_rainy
            sim_df['consecutive_heavy_rain_days'] = sim_heavy
            
            missing_feats = [f for f in features_list if f not in sim_df.columns]
            if missing_feats:
                st.error(f"Missing input for required features: {missing_feats}")
            else:
                X_sim = sim_df[features_list]
                sim_probs = model.predict_proba(X_sim)[:, 1]
                
                sim_df['landslide_probability'] = sim_probs
                sim_df['probability_percent'] = sim_probs * 100
                sim_df['risk_level'] = sim_df['landslide_probability'].apply(assign_risk_level)
                
                # Apply production threshold
                sim_df['is_warning'] = sim_probs >= artifact_threshold
                sim_df['warning_status'] = sim_df['is_warning'].map({True: "WARNING", False: "NO_WARNING"})
                
                warnings_triggered = sim_df['is_warning'].sum()
                
                st.divider()
                st.subheader(f"Simulation Results: {warnings_triggered:,} Warnings Triggered")
                
                # Render the simulated map
                # Render the simulated map
                fig_sim_map = px.scatter_mapbox(
                    sim_df,
                    lat="latitude",
                    lon="longitude",
                    color="risk_level",
                    color_discrete_map=RISK_COLORS,
                    category_orders={"risk_level": RISK_ORDER},
                    size="probability_percent",
                    size_max=18,
                    hover_data={
                        "location_id": True,
                        "landslide_probability": ":.3f",
                        "risk_level": True,
                        "warning_status": True,
                        "elevation_m": ":.1f",
                        "slope_deg": ":.2f",
                        "latitude": False,
                        "longitude": False,
                    },
                    zoom=9,
                    height=600,
                )
                
             # Apply free Esri satellite imagery + Location Labels (Hybrid View)
        fig_map.update_layout(
            mapbox_style="white-bg",
            mapbox_layers=[
                # Base Layer: Satellite Imagery
                {
                    "below": 'traces',
                    "sourcetype": "raster",
                    "sourceattribution": "Esri Satellite",
                    "source": [
                        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    ]
                },
                # Overlay Layer: Location Names & Boundaries
                {
                    "below": 'traces',
                    "sourcetype": "raster",
                    "sourceattribution": "Esri Labels",
                    "source": [
                        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                    ]
                }
            ],
            margin=dict(l=0, r=0, t=0, b=0)
        )
