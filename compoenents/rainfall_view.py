"""
NEXORA Command Center — Rainfall Intelligence Component
Provides real-time precipitation tracking, historical daily logs, and monsoon streak analysis.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from config import RAINY_DAY_THRESHOLD_MM, HEAVY_RAIN_DAY_THRESHOLD_MM, DAILY_RAINFALL_LOG_CSV


def _compute_max_heavy_streak_from_log(threshold_mm: float) -> int:
    """
    Reads the full daily log CSV and computes the maximum consecutive-day
    heavy-rain streak across ALL grids and ALL recorded dates.

    This is needed because `latest_df` only holds features for `as_of_date`
    (today), and if today's rain is below the threshold the live streak is 0
    even though a heavy-rain event occurred recently in the log.
    """
    try:
        log = pd.read_csv(DAILY_RAINFALL_LOG_CSV)
        log["date"] = pd.to_datetime(log["date"], errors="coerce")
        log = log.dropna(subset=["date", "rainfall_mm_day"])
        log = log.sort_values(["grid_id", "date"])

        max_streak = 0
        for _, group in log.groupby("grid_id"):
            group = group.sort_values("date").reset_index(drop=True)
            streak = 0
            prev_date = None
            for _, row in group.iterrows():
                consecutive = (
                    prev_date is not None
                    and (row["date"] - prev_date).days == 1
                )
                if row["rainfall_mm_day"] >= threshold_mm:
                    streak = (streak + 1) if consecutive else 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
                prev_date = row["date"]
        return max_streak
    except Exception:
        return 0


def render_rainfall_view(latest_df: pd.DataFrame):
    """Renders the comprehensive Rainfall Intelligence dashboard."""
    st.markdown(
        """
        <div class="command-panel">
            <div class="panel-header">
                <div class="panel-title">🌧️ RAINFALL INTELLIGENCE &amp; MONSOON TELEMETRY</div>
                <div style="font-size: 0.72rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
                    OPEN-METEO IST REAL-TIME SENSING • CALENDAR-DAY STRICT LOG
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if latest_df.empty:
        st.warning("No rainfall telemetry available.")
        return

    avg_rain = float(latest_df["rainfall_mm"].mean())
    max_rain = float(latest_df["rainfall_mm"].max())
    max_streak = int(latest_df["consecutive_rainy_days"].max())

    # Heavy rain streak must be computed across the full daily log, not just
    # today's latest_df — today's rain may be below threshold (streak = 0 today)
    # even when a heavy event occurred earlier this week.
    max_heavy_streak = _compute_max_heavy_streak_from_log(HEAVY_RAIN_DAY_THRESHOLD_MM)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card cyan">
                <div class="metric-label">Mean Daily Rainfall</div>
                <div class="metric-value">{avg_rain:.1f} <span style="font-size: 0.9rem;">mm</span></div>
                <div class="metric-subtext">Across 419 stations</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card {'warning' if max_rain >= 25 else 'cyan'}">
                <div class="metric-label">Peak Station Rainfall</div>
                <div class="metric-value">{max_rain:.1f} <span style="font-size: 0.9rem;">mm</span></div>
                <div class="metric-subtext">Threshold: {HEAVY_RAIN_DAY_THRESHOLD_MM} mm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card {'warning' if max_streak >= 5 else 'safe'}">
                <div class="metric-label">Longest Rainy Streak</div>
                <div class="metric-value">{max_streak} <span style="font-size: 0.9rem;">days</span></div>
                <div class="metric-subtext">≥ {RAINY_DAY_THRESHOLD_MM} mm/day continuous</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card {'critical' if max_heavy_streak >= 2 else 'safe'}">
                <div class="metric-label">Heavy Rain Streak</div>
                <div class="metric-value">{max_heavy_streak} <span style="font-size: 0.9rem;">days</span></div>
                <div class="metric-subtext">≥ {HEAVY_RAIN_DAY_THRESHOLD_MM} mm/day continuous</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Rainfall vs Stations Histogram
    st.markdown("#### 📊 Station Rainfall Distribution")

    fig_hist = px.histogram(
        latest_df,
        x="rainfall_mm",
        nbins=25,
        labels={"rainfall_mm": "Daily Precipitation (mm)", "count": "Station Count"},
        color_discrete_sequence=["#38bdf8"],
    )
    fig_hist.add_vline(
        x=RAINY_DAY_THRESHOLD_MM,
        line_dash="dot",
        line_color="#10b981",
        annotation_text=f"Rainy Day Threshold ({RAINY_DAY_THRESHOLD_MM}mm)",
        annotation_position="top right",
    )
    fig_hist.add_vline(
        x=HEAVY_RAIN_DAY_THRESHOLD_MM,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text=f"Heavy Rain Day ({HEAVY_RAIN_DAY_THRESHOLD_MM}mm)",
        annotation_position="top right",
    )
    fig_hist.update_layout(
        paper_bgcolor="rgba(15, 23, 42, 0.6)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        height=320,
        margin=dict(l=30, r=20, t=30, b=30),
        font=dict(color="#e2e8f0"),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
        yaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    # Grid Daily Log Table
    st.markdown("#### 📋 Persistent Daily Rainfall Log")
    try:
        daily_log_df = pd.read_csv(DAILY_RAINFALL_LOG_CSV)
        st.dataframe(daily_log_df.tail(100), use_container_width=True, height=280)
    except Exception:
        st.info("Daily grid log file being updated.")
