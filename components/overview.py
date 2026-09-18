"""
NEXORA Command Center — Unified Overview Dashboard Component
Hero screen telling the complete disaster intelligence story in 10-20 seconds:
WHAT IS HAPPENING → WHERE IS IT HAPPENING → WHY IS IT HAPPENING → WHAT DOES AI PREDICT → WHAT IS ON THE GROUND.
"""

from typing import List, Dict

import pandas as pd
import streamlit as st

from components.risk_map import render_risk_map, RISK_COLORS
from citizen_reporting import load_citizen_reports
from geocoding import enrich_with_location_names, get_location_name, format_location_display


def render_overview(
    latest_df: pd.DataFrame,
    history_df: pd.DataFrame,
    risk_summary: dict,
    operating_threshold: float = 0.47,
    citizen_reports: List[Dict] = None,
):
    """Renders the main Unified Overview Command Dashboard with human-readable locality names and coordinates fallback."""
    latest_df = enrich_with_location_names(latest_df)

    if citizen_reports is None:
        citizen_reports = load_citizen_reports()

    # Title & Subtitle
    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <div style="font-size: 1.5rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em;">
                AIZAWL DISASTER SITUATION &amp; EARLY WARNING MATRIX
            </div>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 2px;">
                Real-time spatial monitoring of precipitation, slope susceptibility, and emerging landslide hazard across Aizawl District.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Calculate real KPIs from current data
    total_locations = int(risk_summary.get("total_locations", len(latest_df)))
    warnings_count = int(risk_summary.get("warnings", (latest_df["warning_status"] == "WARNING").sum()))
    high_critical_count = int(latest_df["risk_level"].isin(["HIGH", "CRITICAL"]).sum())
    mean_prob = float(risk_summary.get("mean_landslide_probability", latest_df["landslide_probability"].mean()))
    peak_rain = float(latest_df["rainfall_mm"].max()) if not latest_df.empty else 0.0

    # 4 Prominent KPI Cards
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f"""
            <div class="metric-card critical">
                <div class="metric-label">Active Model Warnings 🚨</div>
                <div class="metric-value">{warnings_count:,}</div>
                <div class="metric-subtext">Stations above {operating_threshold:.2f} threshold</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
            <div class="metric-card cyan">
                <div class="metric-label">Monitored Stations 🛰️</div>
                <div class="metric-value">{total_locations:,}</div>
                <div class="metric-subtext">35 Grid Centroids in Aizawl</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
            <div class="metric-card warning">
                <div class="metric-label">High / Critical Zones ⚠️</div>
                <div class="metric-value">{high_critical_count:,}</div>
                <div class="metric-subtext">Immediate vulnerability tier</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            f"""
            <div class="metric-card cyan">
                <div class="metric-label">Peak Station Rainfall 🌧️</div>
                <div class="metric-value">{peak_rain:.1f} <span style="font-size: 0.9rem;">mm</span></div>
                <div class="metric-subtext">Mean Landslide Prob: {mean_prob*100:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Main Grid: Left = Hero Map (Col 8), Right = AI & Rainfall Telemetry (Col 4)
    col_map, col_intel = st.columns([7, 5])

    with col_map:
        render_risk_map(
            latest_df=latest_df,
            citizen_reports=citizen_reports,
            height=580,
            title="LIVE AIZAWL GIS RISK MAP",
            show_controls=True,
            key_prefix="overview_map",
        )

    with col_intel:
        # AI Risk Engine Card
        st.markdown(
            f"""
            <div class="command-panel" style="margin-bottom: 14px;">
                <div class="panel-header">
                    <div class="panel-title">🧠 RISK ENGINE STATUS</div>
                    <span class="risk-badge {'critical' if warnings_count > 0 else 'low'}">
                        {'HIGH ALERT' if warnings_count > 50 else 'NORMAL'}
                    </span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase;">Mean District Risk</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: #38bdf8; font-family: 'JetBrains Mono', monospace;">
                            {mean_prob*100:.1f}%
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase;">Operating Threshold</div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc; font-family: 'JetBrains Mono', monospace;">
                            {operating_threshold:.2f}
                        </div>
                    </div>
                </div>
                <div style="font-size: 0.75rem; color: #cbd5e1; line-height: 1.4; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">
                    <strong>6 Input Drivers:</strong> Elevation, Slope Angle, 1-Day Precipitation, Total Rainfall, Rainy Streak, Heavy Rain Streak.<br>
                    <strong>Model:</strong> Production Random Forest (Scikit-Learn 1.6.1).
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Rainfall Intelligence Card
        avg_rain = float(latest_df["rainfall_mm"].mean()) if not latest_df.empty else 0.0
        max_streak = int(latest_df["consecutive_rainy_days"].max()) if not latest_df.empty else 0
        max_h_streak = int(latest_df["consecutive_heavy_rain_days"].max()) if not latest_df.empty else 0

        st.markdown(
            f"""
            <div class="command-panel">
                <div class="panel-header">
                    <div class="panel-title">🌧️ RAINFALL TELEMETRY (IST)</div>
                    <span style="font-size: 0.7rem; color: #34d399; font-weight: 700;">● REAL-TIME</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                    <div style="background: rgba(15,23,42,0.6); padding: 8px 10px; border-radius: 8px;">
                        <div style="font-size: 0.68rem; color: #94a3b8;">MEAN RAINFALL</div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">{avg_rain:.1f} mm</div>
                    </div>
                    <div style="background: rgba(15,23,42,0.6); padding: 8px 10px; border-radius: 8px;">
                        <div style="font-size: 0.68rem; color: #94a3b8;">PEAK RAINFALL</div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #38bdf8;">{peak_rain:.1f} mm</div>
                    </div>
                    <div style="background: rgba(15,23,42,0.6); padding: 8px 10px; border-radius: 8px;">
                        <div style="font-size: 0.68rem; color: #94a3b8;">RAINY STREAK</div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #f59e0b;">{max_streak} days</div>
                    </div>
                    <div style="background: rgba(15,23,42,0.6); padding: 8px 10px; border-radius: 8px;">
                        <div style="font-size: 0.68rem; color: #94a3b8;">HEAVY RAIN STREAK</div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #ef4444;">{max_h_streak} days</div>
                    </div>
                </div>
                <div style="font-size: 0.72rem; color: #64748b;">
                    Strict calendar-day gap policy. Synced hourly via Open-Meteo Aizawl centroids.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Bottom Split: Left = Active Warning Feed (Col 6), Right = Ground Hazard Evidence (Col 6)
    col_warn, col_cit = st.columns(2)

    with col_warn:
        st.markdown(
            """
            <div class="command-panel" style="height: 100%;">
                <div class="panel-header">
                    <div class="panel-title">🚨 TOP IMMINENT HAZARD WARNINGS</div>
                    <span style="font-size: 0.72rem; color: #f87171; font-weight: 700;">PRIORITY DISPATCH</span>
                </div>
            """,
            unsafe_allow_html=True,
        )

        top_warnings = latest_df[latest_df["warning_status"] == "WARNING"].sort_values(
            "landslide_probability", ascending=False
        ).head(5)

        if top_warnings.empty:
            st.info("✅ No active landslide warnings triggered at current rainfall levels.")
        else:
            for _, w_row in top_warnings.iterrows():
                p_val = float(w_row["landslide_probability"])
                r_level = str(w_row["risk_level"])
                lat_val = float(w_row["latitude"])
                lon_val = float(w_row["longitude"])
                l_name = w_row.get("location_name") or get_location_name(lat_val, lon_val)

                # If locality name is a specific landmark vs coordinate fallback
                coord_str = f"{lat_val:.4f}° N, {lon_val:.4f}° E"
                heading_title = f"📍 {l_name}" if l_name and "°" not in l_name else f"📍 {coord_str}"

                st.markdown(
                    f"""
                    <div class="warning-item">
                        <div>
                            <div style="font-weight: 800; font-size: 0.88rem; color: #f8fafc;">
                                {heading_title}
                            </div>
                            <div style="font-size: 0.72rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace; margin-top: 1px;">
                                {coord_str} • Elevation: {w_row['elevation_m']:.0f}m | Slope: {w_row['slope_deg']:.1f}°
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span class="risk-badge {r_level.lower()}">{r_level}</span>
                            <div style="font-weight: 800; font-size: 0.95rem; color: #ef4444; font-family: 'JetBrains Mono', monospace; margin-top: 3px;">
                                {p_val*100:.1f}%
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    with col_cit:
        st.markdown(
            """
            <div class="command-panel" style="height: 100%;">
                <div class="panel-header">
                    <div class="panel-title">📷 RECENT CITIZEN GROUND EVIDENCE</div>
                    <span style="font-size: 0.72rem; color: #38bdf8; font-weight: 700;">FIELD REPORTS</span>
                </div>
            """,
            unsafe_allow_html=True,
        )

        recent_reports = citizen_reports[:3] if citizen_reports else []

        if not recent_reports:
            st.info("No ground reports submitted yet.")
        else:
            for rep in recent_reports:
                r_lat = float(rep.get("latitude", 23.7388))
                r_lon = float(rep.get("longitude", 92.6963))
                r_loc = get_location_name(r_lat, r_lon)
                coord_str = f"{r_lat:.4f}° N, {r_lon:.4f}° E"
                r_title = f"{r_loc}" if r_loc and "°" not in r_loc else coord_str

                st.markdown(
                    f"""
                    <div class="citizen-card" style="padding: 10px 12px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: #38bdf8; font-size: 0.82rem;">📷 {rep.get('report_type', 'Hazard')} — {r_title}</strong>
                            <span style="font-size: 0.68rem; color: #f59e0b; border: 1px solid #f59e0b; padding: 1px 6px; border-radius: 4px;">
                                {rep.get('status', 'Pending')}
                            </span>
                        </div>
                        <div style="font-size: 0.74rem; color: #cbd5e1; margin: 4px 0;">
                            {rep.get('description', '')[:110]}...
                        </div>
                        <div style="font-size: 0.68rem; color: #64748b; font-family: 'JetBrains Mono', monospace;">
                            📍 {coord_str} | Nearest Station: {rep.get('nearest_zone_id', 'AIZ_GRID')} ({rep.get('distance_to_zone_m', 0)}m)
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if st.button("🚨 SUBMIT NEW GROUND HAZARD REPORT", key="overview_submit_hazard_btn", type="primary", use_container_width=True):
            st.session_state["active_nav"] = "🚨 Report Ground Hazard"
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
