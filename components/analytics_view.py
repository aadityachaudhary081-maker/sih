"""
NEXORA Command Center — Analytics & Distribution Component
Provides geospatial and statistical risk distributions across Aizawl district.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from components.risk_map import RISK_COLORS, RISK_ORDER


def render_analytics_view(latest_df: pd.DataFrame, operating_threshold: float = 0.47):
    """Renders the comprehensive Analytics & Statistical Distribution dashboard."""
    st.markdown(
        """
        <div class="command-panel">
            <div class="panel-header">
                <div class="panel-title">📊 STATISTICAL ANALYTICS &amp; RISK DISTRIBUTIONS</div>
                <div style="font-size: 0.72rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
                    POPULATION RISK SPREAD • CORRELATION MATRICES • PROBABILITY HISTOGRAMS
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if latest_df.empty:
        st.warning("No analytics data available.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📈 Visual Risk Category Breakdown")
        risk_counts = latest_df["risk_level"].value_counts().reindex(RISK_ORDER, fill_value=0)
        fig_risk = px.bar(
            x=risk_counts.index,
            y=risk_counts.values,
            color=risk_counts.index,
            color_discrete_map=RISK_COLORS,
            category_orders={"x": RISK_ORDER},
            labels={"x": "Risk Category", "y": "Monitored Stations Count"},
        )
        fig_risk.update_layout(
            showlegend=False,
            height=320,
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=30, r=20, t=20, b=30),
            xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
            yaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
        )
        st.plotly_chart(fig_risk, use_container_width=True)

    with col2:
        st.markdown("#### 🎯 Model Probability Density")
        fig_prob = px.histogram(
            latest_df,
            x="landslide_probability",
            nbins=30,
            labels={"landslide_probability": "Landslide Probability", "count": "Station Count"},
            color_discrete_sequence=["#38bdf8"],
        )
        fig_prob.add_vline(
            x=operating_threshold,
            line_dash="dash",
            line_color="#ef4444",
            annotation_text=f"Decision Threshold ({operating_threshold:.2f})",
            annotation_position="top right",
            annotation_font_color="#ef4444",
        )
        fig_prob.update_layout(
            height=320,
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=30, r=20, t=20, b=30),
            xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
            yaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
        )
        st.plotly_chart(fig_prob, use_container_width=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("#### 🌧️ Daily Rainfall vs Probability")
        fig_rf = px.scatter(
            latest_df,
            x="rainfall_mm",
            y="landslide_probability",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
            category_orders={"risk_level": RISK_ORDER},
            hover_data=["location_id", "slope_deg"],
            labels={"rainfall_mm": "Rainfall (mm)", "landslide_probability": "Probability"},
        )
        fig_rf.update_layout(
            height=340,
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=30, r=20, t=20, b=30),
            xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
            yaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
        )
        st.plotly_chart(fig_rf, use_container_width=True)

    with col4:
        st.markdown("#### 🏔️ Slope Gradient vs Probability")
        fig_slope = px.scatter(
            latest_df,
            x="slope_deg",
            y="landslide_probability",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
            category_orders={"risk_level": RISK_ORDER},
            hover_data=["location_id", "elevation_m"],
            labels={"slope_deg": "Slope Angle (degrees)", "landslide_probability": "Probability"},
        )
        fig_slope.update_layout(
            height=340,
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=30, r=20, t=20, b=30),
            xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
            yaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)"),
        )
        st.plotly_chart(fig_slope, use_container_width=True)
