"""
NEXORA Command Center — Location Intelligence Component
Provides deep inspection for any of the 419 monitored stations in Aizawl with exact locality names.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from geocoding import enrich_with_location_names, get_location_name

TREND_GAP_THRESHOLD_DAYS = 30


def find_trend_gaps(dates: pd.Series, threshold_days: int = TREND_GAP_THRESHOLD_DAYS):
    """Detects gaps wider than threshold_days between consecutive monitoring records."""
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
    """Inserts None rows across gaps so Plotly breaks the line instead of interpolating."""
    working = loc_history[["date", "landslide_probability"]].dropna(subset=["date"]).copy()
    gaps = find_trend_gaps(working["date"], threshold_days=threshold_days)
    if not gaps:
        return working, gaps

    break_rows = pd.DataFrame({
        "date": [gap_start + pd.Timedelta(hours=12) for gap_start, _ in gaps],
        "landslide_probability": [None] * len(gaps),
    })
    plot_df = pd.concat([working, break_rows], ignore_index=True).sort_values("date").reset_index(drop=True)
    return plot_df, gaps


def render_location_drawer(latest_df: pd.DataFrame, history_df: pd.DataFrame, operating_threshold: float = 0.47):
    """Renders the comprehensive Location Intelligence drawer/panel with human-readable locality names."""
    latest_df = enrich_with_location_names(latest_df)

    st.markdown(
        """
        <div class="command-panel">
            <div class="panel-header">
                <div class="panel-title">📍 LOCATION INTELLIGENCE &amp; LOCALITY SUSCEPTIBILITY INSPECTOR</div>
                <div style="font-size: 0.72rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
                    EXACT LOCALITY TELEMETRY • MULTI-PARAM DECOMPOSITION
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Format location selector labels with both Node ID and exact human-readable locality name
    location_options = latest_df["location_id"].tolist()
    location_label_map = {
        row["location_id"]: f"📍 {row.get('location_name', 'Aizawl')} — {row['location_id']} ({row['risk_level']})"
        for _, row in latest_df.iterrows()
    }

    selected_location = st.selectbox(
        "Select Monitored Location Node / Locality:",
        location_options,
        format_func=lambda x: location_label_map.get(x, x),
        key="location_drawer_selector",
    )

    loc_row = latest_df[latest_df["location_id"] == selected_location].iloc[0]
    loc_name = loc_row.get("location_name") or get_location_name(float(loc_row["latitude"]), float(loc_row["longitude"]))

    prob = float(loc_row["landslide_probability"])
    prob_pct = prob * 100
    risk_level = str(loc_row["risk_level"])
    is_warning = (loc_row["warning_status"] == "WARNING") or (prob >= operating_threshold)

    # Top Status & Coordinates Banner
    st.markdown(
        f"""
        <div style="background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 18px 22px; margin-bottom: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 1.3rem; font-weight: 800; color: #f8fafc;">
                        📍 {loc_name}
                    </div>
                    <div style="font-size: 0.78rem; color: #38bdf8; font-family: 'JetBrains Mono', monospace; margin-top: 3px;">
                        NODE: <strong>{selected_location}</strong> | LAT: <strong>{loc_row['latitude']:.6f}° N</strong> | LON: <strong>{loc_row['longitude']:.6f}° E</strong>
                    </div>
                </div>
                <div style="text-align: right;">
                    <span class="risk-badge {risk_level.lower()}" style="font-size: 0.85rem; padding: 6px 14px;">{risk_level} RISK</span>
                    <div style="font-weight: 800; font-size: 0.9rem; color: {'#ef4444' if is_warning else '#10b981'}; margin-top: 4px;">
                        {'🚨 WARNING TRIGGERED' if is_warning else '✅ WITHIN SAFE LIMITS'}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Key Metrics Grid
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card {'critical' if is_warning else 'safe'}">
                <div class="metric-label">Landslide Probability</div>
                <div class="metric-value">{prob_pct:.1f}%</div>
                <div class="metric-subtext">Raw Probability: {prob:.4f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card cyan">
                <div class="metric-label">Terrain Elevation</div>
                <div class="metric-value">{loc_row['elevation_m']:.0f} <span style="font-size: 0.9rem;">m</span></div>
                <div class="metric-subtext">Slope Gradient: {loc_row['slope_deg']:.1f}°</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card cyan">
                <div class="metric-label">Today's Rainfall</div>
                <div class="metric-value">{loc_row['rainfall_mm']:.1f} <span style="font-size: 0.9rem;">mm</span></div>
                <div class="metric-subtext">1-Day Prior: {loc_row['rainfall_1d_mm']:.1f} mm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card {'warning' if loc_row['consecutive_rainy_days'] > 3 else 'safe'}">
                <div class="metric-label">Rainy Streak</div>
                <div class="metric-value">{int(loc_row['consecutive_rainy_days'])} <span style="font-size: 0.9rem;">days</span></div>
                <div class="metric-subtext">Heavy Rain Streak: {int(loc_row['consecutive_heavy_rain_days'])} days</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ML Explanation & Feature Breakdown Card
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown(
            f"""
            <div class="command-panel" style="height: 100%;">
                <div class="panel-header">
                    <div class="panel-title">🧠 RISK ENGINE ASSESSMENT</div>
                </div>
                <div style="font-size: 0.82rem; line-height: 1.6; color: #cbd5e1;">
                    The production Random Forest model operates with an active threshold of <strong>{operating_threshold:.2f} ({operating_threshold*100:.0f}%)</strong>.<br><br>
                    • Locality: <strong style="color: #38bdf8;">{loc_name}</strong><br>
                    • Current Probability: <strong style="color: {'#f87171' if is_warning else '#34d399'};">{prob:.4f} ({prob_pct:.1f}%)</strong><br>
                    • Binary Model Decision: <strong>{loc_row['warning_status']}</strong><br>
                    • Visual Presentation Band: <strong style="color: #38bdf8;">{risk_level}</strong><br><br>
                    <span style="font-size: 0.75rem; color: #94a3b8;">
                        <em>Note: WARNING/NO_WARNING represents the official binary model decision. Risk bands provide refined visualization gradients for district planning.</em>
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            f"""
            <div class="command-panel" style="height: 100%;">
                <div class="panel-header">
                    <div class="panel-title">🏔️ TOPOGRAPHIC &amp; RAIN DRIVERS</div>
                </div>
                <div style="font-size: 0.82rem; line-height: 1.7; color: #e2e8f0;">
                    • <strong>Elevation:</strong> {loc_row['elevation_m']:.1f} meters (DEM)<br>
                    • <strong>Slope Gradient:</strong> {loc_row['slope_deg']:.2f} degrees<br>
                    • <strong>Current Daily Rainfall:</strong> {loc_row['rainfall_mm']:.2f} mm<br>
                    • <strong>Consecutive Rainy Days (≥1.0mm):</strong> {int(loc_row['consecutive_rainy_days'])} days<br>
                    • <strong>Consecutive Heavy Rain Days (≥25.0mm):</strong> {int(loc_row['consecutive_heavy_rain_days'])} days
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Historical Time Series
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 📈 Historical Risk Trajectory")

    loc_history = history_df[history_df["location_id"] == selected_location].sort_values("date")

    if not loc_history.empty:
        plot_df, gaps = build_gap_broken_trend(loc_history, TREND_GAP_THRESHOLD_DAYS)

        if gaps:
            st.info(
                f"ℹ️ {len(gaps)} monitoring gap(s) (>30 days) detected and visually broken to prevent artificial line interpolation."
            )

        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Scatter(
                x=plot_df["date"],
                y=plot_df["landslide_probability"],
                mode="lines+markers",
                name="Landslide Probability",
                line=dict(color="#38bdf8", width=2.5),
                marker=dict(size=6, color="#0284c7"),
                connectgaps=False,
            )
        )
        fig_trend.add_hline(
            y=operating_threshold,
            line_dash="dash",
            line_color="#ef4444",
            annotation_text=f"Operating Threshold ({operating_threshold:.2f})",
            annotation_position="top left",
            annotation_font_color="#ef4444",
        )
        fig_trend.update_layout(
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            height=360,
            margin=dict(l=40, r=20, t=30, b=30),
            yaxis=dict(
                title="Probability",
                range=[0, 1.05],
                gridcolor="rgba(255, 255, 255, 0.06)",
                zerolinecolor="rgba(255, 255, 255, 0.1)",
            ),
            xaxis=dict(
                title="Date",
                gridcolor="rgba(255, 255, 255, 0.06)",
            ),
            font=dict(color="#e2e8f0"),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No prior historical records logged for this specific location node.")
