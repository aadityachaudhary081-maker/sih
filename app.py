"""
NEXORA — AI DISASTER INTELLIGENCE CENTER
Aizawl District, Mizoram, North-East India
Landslide Early Warning, Geospatial Monitoring & Citizen Ground Reporting Platform
"""

import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st

# Custom Styles & Design System
from styles import COMMAND_CENTER_CSS

# Storage & Locality Telemetry Systems
from citizen_reporting import load_citizen_reports
from geocoding import enrich_with_location_names
from generate_predictions import load_artifact, assign_risk_level, MODEL_ARTIFACT_PATH
from config import RAINY_DAY_THRESHOLD_MM, HEAVY_RAIN_DAY_THRESHOLD_MM

# Command Center UI Components
from components.header import render_header
from components.sidebar import render_sidebar
from components.right_drawer import render_right_drawer
from components.overview import render_overview
from components.risk_map import render_risk_map
from components.location_drawer import render_location_drawer
from components.whatif_simulation import render_whatif_simulation
from components.rainfall_view import render_rainfall_view
from components.warning_center import render_warning_center
from components.citizen_feed import render_report_hazard_view
from components.analytics_view import render_analytics_view
from components.system_health import render_system_health

# --------------------------------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="NEXORA — Disaster Intelligence Center",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Command Center Custom Styles
st.markdown(COMMAND_CENTER_CSS, unsafe_allow_html=True)

DATA_DIR = "data"
LATEST_RISK_PATH = os.path.join(DATA_DIR, "latest_location_risk.csv")
ALL_PREDICTIONS_PATH = os.path.join(DATA_DIR, "all_daily_live_predictions.csv")
RISK_SUMMARY_PATH = os.path.join(DATA_DIR, "risk_summary.json")

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
# DATA VALIDATION & INGESTION
# --------------------------------------------------------------------------
def validate_files_exist():
    """Validates that real Phase 9 / 11 production data files exist."""
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
            "### Required Production Data Missing\n\n"
            + "\n".join(missing)
            + "\n\nPlease run `python generate_predictions.py` to populate live prediction data."
        )
        st.stop()


CACHE_TTL_SECONDS = 600  # 10 min cache for high responsiveness


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
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
    # Enrich with human-readable location names across entire website
    df = enrich_with_location_names(df)
    return df


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


# Execute validation & load
validate_files_exist()
latest_df = load_csv(LATEST_RISK_PATH)
history_df = load_csv(ALL_PREDICTIONS_PATH)
risk_summary = load_json(RISK_SUMMARY_PATH)
citizen_reports = load_citizen_reports()

# Get production operating threshold dynamically (default 0.47)
operating_threshold = float(risk_summary.get("operating_threshold", 0.47))

# --------------------------------------------------------------------------
# SIDEBAR & TOP HEADER RENDERING
# --------------------------------------------------------------------------
active_nav, data_mode = render_sidebar()

# If user switched operating mode to simulation, route directly to What-If
if data_mode == "What-if Simulation" and active_nav == "◉ Command Overview":
    active_nav = "🧪 What-if Simulation"

render_header(risk_summary=risk_summary, data_mode=data_mode)

# Render Slide-Over Hamburger Control Panel if toggled
render_right_drawer(risk_summary=risk_summary, data_mode=data_mode)

# --------------------------------------------------------------------------
# ROUTING & MAIN VIEW RENDERING
# --------------------------------------------------------------------------
if active_nav == "◉ Command Overview":
    render_overview(
        latest_df=latest_df,
        history_df=history_df,
        risk_summary=risk_summary,
        operating_threshold=operating_threshold,
        citizen_reports=citizen_reports,
    )

elif active_nav == "🚨 Report Ground Hazard":
    render_report_hazard_view(latest_df=latest_df)

elif active_nav == "🗺️ Live GIS Risk Map":
    render_risk_map(
        latest_df=latest_df,
        citizen_reports=citizen_reports,
        height=650,
        title="AIZAWL DISTRICT LIVE GIS RISK MAP & GROUND EVIDENCE OVERLAY",
        show_controls=True,
        key_prefix="standalone_map",
    )

elif active_nav == "📍 Location Intelligence":
    render_location_drawer(
        latest_df=latest_df,
        history_df=history_df,
        operating_threshold=operating_threshold,
    )

elif active_nav == "🧠 Risk Engine":
    st.markdown("### 🧠 Production Landslide Risk Model")
    st.markdown(
        """
        The NEXORA platform employs a calibrated **Random Forest Classifier** trained on historical Aizawl slope failures,
        topographic parameters, and monsoon precipitation dynamics.
        """
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="command-panel">
                <div class="panel-header">
                    <div class="panel-title">📐 MODEL FEATURE SPECIFICATION</div>
                </div>
                <div style="font-size: 0.85rem; line-height: 1.7;">
                    1. <code>elevation_m</code>: Digital Elevation Model terrain height (meters)<br>
                    2. <code>slope_deg</code>: Local slope gradient in degrees (0° to 90°)<br>
                    3. <code>rainfall_mm</code>: Today's IST cumulative precipitation (mm)<br>
                    4. <code>rainfall_1d_mm</code>: 1-Day previous cumulative rainfall (mm)<br>
                    5. <code>consecutive_rainy_days</code>: Streak of continuous days with ≥ 1.0mm rain<br>
                    6. <code>consecutive_heavy_rain_days</code>: Streak of continuous days with ≥ 25.0mm rain
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="command-panel">
                <div class="panel-header">
                    <div class="panel-title">⚖️ CALIBRATED DECISION THRESHOLDS</div>
                </div>
                <div style="font-size: 0.85rem; line-height: 1.7;">
                    • <strong>Binary Decision Threshold:</strong> <span style="color: #38bdf8; font-weight: 700;">{operating_threshold:.2f} ({operating_threshold*100:.0f}%)</span><br>
                    • <strong>Classification Rule:</strong> <code>Prob ≥ {operating_threshold:.2f} → WARNING</code><br>
                    • <strong>Visual Presentation Categories:</strong><br>
                    &nbsp;&nbsp;🟢 <code>0.00 – 0.24</code>: LOW RISK<br>
                    &nbsp;&nbsp;🟡 <code>0.25 – 0.46</code>: MODERATE RISK<br>
                    &nbsp;&nbsp;🟠 <code>0.47 – 0.74</code>: HIGH RISK (WARNING)<br>
                    &nbsp;&nbsp;🔴 <code>0.75 – 1.00</code>: CRITICAL RISK (WARNING)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    render_analytics_view(latest_df=latest_df, operating_threshold=operating_threshold)

elif active_nav == "🧪 What-if Simulation":
    render_whatif_simulation(latest_df=latest_df)

elif active_nav == "🌧️ Rainfall Intelligence":
    render_rainfall_view(latest_df=latest_df)

elif active_nav == "🚨 Early Warning Center":
    render_warning_center(latest_df=latest_df, operating_threshold=operating_threshold)

elif active_nav == "📊 Analytics & Distribution":
    render_analytics_view(latest_df=latest_df, operating_threshold=operating_threshold)

elif active_nav == "⚙️ System Health":
    render_system_health(risk_summary=risk_summary)

# --------------------------------------------------------------------------
# FOOTER
# --------------------------------------------------------------------------
st.markdown("<hr style='border: none; border-top: 1px solid rgba(255, 255, 255, 0.06); margin: 30px 0 14px 0;'>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; color: #64748b;">
        <div>
            <strong>NEXORA DISASTER INTELLIGENCE CENTER</strong> • SMART INDIA HACKATHON
        </div>
        <div>
            Mizoram State Disaster Management Authority (MSDMA) Telemetry Protocol
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
