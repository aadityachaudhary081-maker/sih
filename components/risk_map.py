"""
NEXORA Command Center — GIS Interactive Risk Map Component
Supports:
- Esri Satellite Imagery + Place Labels Hybrid Base
- Real Human-Readable Locality Names (e.g. Chaltlang, Durtlang, Bawngkawn, Tlangnuam)
- Dual-layer AI Risk Points + Geotagged Citizen Hazard Markers (📷)
- Dynamic multi-tier filtering (Risk Levels, Warning Status, Min Probability)
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from typing import List, Dict, Optional

from geocoding import enrich_with_location_names, get_location_name

RISK_ORDER = ["LOW", "MODERATE", "HIGH", "CRITICAL"]

RISK_COLORS = {
    "LOW": "#10b981",       # Emerald Green
    "MODERATE": "#f59e0b",  # Amber Yellow
    "HIGH": "#f97316",      # Bright Orange
    "CRITICAL": "#ef4444",  # Crimson Red
}


def render_risk_map(
    latest_df: pd.DataFrame,
    citizen_reports: Optional[List[Dict]] = None,
    height: int = 600,
    title: str = "LIVE AIZAWL GIS RISK INTELLIGENCE MAP",
    show_controls: bool = True,
    key_prefix: str = "main_map",
):
    """Renders the comprehensive GIS command center risk map with locality names."""

    # Ensure dataframe has human-readable location names
    latest_df = enrich_with_location_names(latest_df)

    st.markdown(
        f"""
        <div class="command-panel" style="padding: 14px 18px 8px 18px; margin-bottom: 12px;">
            <div class="panel-header" style="margin-bottom: 8px;">
                <div class="panel-title">🛰️ {title}</div>
                <div style="font-size: 0.72rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
                    ESRI HYBRID SATELLITE • 419 MONITORING NODES • LOCALITY ENRICHED
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if show_controls:
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
        with c1:
            risk_filter = st.multiselect(
                "Risk Bands", RISK_ORDER, default=RISK_ORDER, key=f"{key_prefix}_risk_filter"
            )
        with c2:
            warning_filter = st.selectbox(
                "Warning State", ["ALL", "WARNING", "NO_WARNING"], key=f"{key_prefix}_warning_filter"
            )
        with c3:
            min_prob = st.slider(
                "Min Probability", 0.0, 1.0, 0.0, 0.05, key=f"{key_prefix}_min_prob"
            )
        with c4:
            show_citizen_layer = st.checkbox(
                "📷 Show Citizen Reports", value=True, key=f"{key_prefix}_citizen_toggle"
            )
    else:
        risk_filter = RISK_ORDER
        warning_filter = "ALL"
        min_prob = 0.0
        show_citizen_layer = True

    # Filter AI risk dataset
    filtered_df = latest_df[latest_df["risk_level"].isin(risk_filter)].copy()
    if warning_filter != "ALL":
        filtered_df = filtered_df[filtered_df["warning_status"] == warning_filter]
    filtered_df = filtered_df[filtered_df["landslide_probability"] >= min_prob]

    # Initialize Plotly Map figure
    fig = go.Figure()

    # Add AI Monitored Nodes by Risk Category with Locality Names
    for risk in RISK_ORDER:
        if risk not in risk_filter:
            continue
        sub_df = filtered_df[filtered_df["risk_level"] == risk]
        if sub_df.empty:
            continue

        hover_texts = [
            f"<b>📍 Locality:</b> {row.get('location_name', 'Aizawl')}<br>"
            f"<b>Node ID:</b> {row['location_id']}<br>"
            f"<b>Landslide Probability:</b> {row['landslide_probability']*100:.1f}% ({row['landslide_probability']:.3f})<br>"
            f"<b>Risk Level:</b> {row['risk_level']}<br>"
            f"<b>Model Decision:</b> {row['warning_status']}<br>"
            f"<b>Elevation:</b> {row.get('elevation_m', 'N/A')} m | <b>Slope:</b> {row.get('slope_deg', 'N/A'):.1f}°<br>"
            f"<b>Today's Rainfall:</b> {row.get('rainfall_mm', 'N/A')} mm<br>"
            f"<b>Rainy Streak:</b> {row.get('consecutive_rainy_days', 0)} days<br>"
            f"<b>Heavy Rain Streak:</b> {row.get('consecutive_heavy_rain_days', 0)} days"
            for _, row in sub_df.iterrows()
        ]

        sizes = [max(8, min(22, p * 22)) for p in sub_df["landslide_probability"]]

        fig.add_trace(
            go.Scattermapbox(
                lat=sub_df["latitude"],
                lon=sub_df["longitude"],
                mode="markers",
                marker=dict(
                    size=sizes,
                    color=RISK_COLORS[risk],
                    opacity=0.85,
                ),
                name=f"{risk}",
                text=hover_texts,
                hoverinfo="text",
            )
        )

    # Add Citizen Ground Reports Layer with exact location names
    if show_citizen_layer and citizen_reports:
        c_lats = [r["latitude"] for r in citizen_reports if "latitude" in r]
        c_lons = [r["longitude"] for r in citizen_reports if "longitude" in r]
        c_hover = [
            f"<b>📷 CITIZEN GROUND REPORT</b><br>"
            f"<b>📍 Location:</b> {get_location_name(r['latitude'], r['longitude'])}<br>"
            f"<b>Incident:</b> {r.get('report_type', 'Observation')}<br>"
            f"<b>Status:</b> {r.get('status', 'Pending')}<br>"
            f"<b>Accuracy:</b> ±{r.get('gps_accuracy_m', 'N/A')} m<br>"
            f"<b>Timestamp:</b> {r.get('timestamp', '')[:16]}<br>"
            f"<b>Nearest Monitoring Zone:</b> {r.get('nearest_zone_id', 'N/A')} ({r.get('distance_to_zone_m', 'N/A')} m)<br>"
            f"<b>Details:</b> {r.get('description', 'No description')}"
            for r in citizen_reports
        ]

        if c_lats:
            fig.add_trace(
                go.Scattermapbox(
                    lat=c_lats,
                    lon=c_lons,
                    mode="markers+text",
                    marker=dict(
                        size=14,
                        color="#38bdf8",
                        symbol="circle",
                    ),
                    text=["📷" for _ in c_lats],
                    textposition="middle center",
                    textfont=dict(size=10, color="#ffffff"),
                    name="📷 Citizen Ground Evidence",
                    hovertext=c_hover,
                    hoverinfo="text",
                )
            )

    # Center map on Aizawl
    center_lat = float(latest_df["latitude"].mean()) if not latest_df.empty else 23.73
    center_lon = float(latest_df["longitude"].mean()) if not latest_df.empty else 92.71

    # Apply Esri Satellite Hybrid Basemap Layers
    fig.update_layout(
        mapbox=dict(
            style="white-bg",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=10.2,
            layers=[
                {
                    "below": "traces",
                    "sourcetype": "raster",
                    "sourceattribution": "Esri World Imagery",
                    "source": [
                        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    ],
                },
                {
                    "below": "traces",
                    "sourcetype": "raster",
                    "sourceattribution": "Esri Reference Places & Roads",
                    "source": [
                        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                    ],
                },
            ],
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        paper_bgcolor="#070a12",
        plot_bgcolor="#070a12",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(11, 15, 25, 0.85)",
            bordercolor="rgba(255, 255, 255, 0.1)",
            borderwidth=1,
            font=dict(size=11, color="#e2e8f0"),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Visualizing {len(filtered_df):,} of {len(latest_df):,} monitoring nodes "
        + (f"and {len(citizen_reports):,} ground reports across Aizawl." if (show_citizen_layer and citizen_reports) else ".")
    )
