"""
NEXORA Command Center — Early Warning Center Component
Prioritizes imminent landslide hazards and active alerts for district authorities with human-readable locality names.
"""

import pandas as pd
import streamlit as st

from geocoding import enrich_with_location_names


def render_warning_center(latest_df: pd.DataFrame, operating_threshold: float = 0.47):
    """Renders the emergency Early Warning Center panel with exact locality names."""
    latest_df = enrich_with_location_names(latest_df)

    st.markdown(
        """
        <div class="command-panel">
            <div class="panel-header">
                <div class="panel-title">🚨 EARLY WARNING CENTER &amp; EMERGENCY ALERT DISPATCH</div>
                <div style="font-size: 0.72rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
                    PRIORITY TRIGGERED HAZARDS • AUTOMATIC ESCALATION PROTOCOL
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    warning_df = latest_df[latest_df["warning_status"] == "WARNING"].copy()
    critical_df = latest_df[latest_df["risk_level"] == "CRITICAL"].copy()
    high_df = latest_df[latest_df["risk_level"] == "HIGH"].copy()

    # KPI Summary Cards
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card critical">
                <div class="metric-label">Active Model Warnings</div>
                <div class="metric-value">{len(warning_df):,}</div>
                <div class="metric-subtext">Nodes over threshold ({operating_threshold:.2f})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card critical">
                <div class="metric-label">CRITICAL Priority Zones</div>
                <div class="metric-value">{len(critical_df):,}</div>
                <div class="metric-subtext">Probability ≥ 75.0%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card warning">
                <div class="metric-label">HIGH Priority Zones</div>
                <div class="metric-value">{len(high_df):,}</div>
                <div class="metric-subtext">Probability 47.0% – 74.9%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Filter Controls
    f_col1, f_col2 = st.columns([2, 1])

    with f_col1:
        selected_band = st.selectbox(
            "Filter Warnings by Visual Category:",
            ["ALL WARNINGS", "CRITICAL ONLY", "HIGH ONLY", "MODERATE", "LOW"],
            key="warning_center_filter"
        )

    with f_col2:
        st.write("")
        st.write("")
        csv_data = warning_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Export Warnings CSV",
            data=csv_data,
            file_name="nexora_aizawl_active_warnings.csv",
            mime="text/csv",
            use_container_width=True,
        )

    display_df = warning_df.copy()
    if selected_band == "CRITICAL ONLY":
        display_df = critical_df
    elif selected_band == "HIGH ONLY":
        display_df = high_df

    display_cols = [
        "location_name", "location_id", "date", "landslide_probability", "probability_percent",
        "risk_level", "warning_status", "rainfall_mm", "consecutive_rainy_days",
        "elevation_m", "slope_deg"
    ]
    valid_cols = [c for c in display_cols if c in display_df.columns]

    sorted_df = display_df.sort_values("landslide_probability", ascending=False)[valid_cols]

    st.markdown(f"Showing **{len(sorted_df)}** active alert node(s):")

    st.dataframe(
        sorted_df.style.format({
            "landslide_probability": "{:.4f}",
            "probability_percent": "{:.1f}%",
            "rainfall_mm": "{:.1f} mm",
            "elevation_m": "{:.0f} m",
            "slope_deg": "{:.1f}°",
        }),
        use_container_width=True,
        height=420,
    )
