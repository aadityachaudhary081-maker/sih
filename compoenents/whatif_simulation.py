"""
NEXORA Command Center — What-If Rainfall & Hazard Simulation Engine
Allows emergency authorities to simulate extreme monsoon precipitation scenarios,
single slope stability, and evaluate district-wide warning triggers in real-time.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from generate_predictions import load_artifact, assign_risk_level, MODEL_ARTIFACT_PATH
from config import RAINY_DAY_THRESHOLD_MM, HEAVY_RAIN_DAY_THRESHOLD_MM
from components.risk_map import RISK_COLORS, RISK_ORDER
from geocoding import enrich_with_location_names, get_location_name


def render_whatif_simulation(latest_df: pd.DataFrame):
    """Renders the comprehensive What-If Simulation Command Panel with locality names."""
    latest_df = enrich_with_location_names(latest_df)

    st.markdown(
        """
        <div class="sim-mode-banner">
            <div>🧪 <strong>WHAT-IF SIMULATION ENVIRONMENT</strong> — Sandbox for disaster planning &amp; emergency drills</div>
            <div style="font-size: 0.75rem; color: #e9d5ff;">MODEL: RANDOM FOREST v1.6</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        artifact = load_artifact(MODEL_ARTIFACT_PATH)
        model = artifact["model"]
        features_list = artifact["features"]
        operating_threshold = float(artifact["operating_threshold"])
    except Exception as e:
        st.error(f"Error loading production ML model artifact: {e}")
        return

    sim_type = st.radio(
        "Select Simulation Scope:",
        ["📍 Single Location Drill", "🗺️ Global District Storm Scenario"],
        horizontal=True,
        key="whatif_scope_radio",
    )

    st.markdown("<hr style='border: none; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 14px 0;'>", unsafe_allow_html=True)

    if sim_type == "📍 Single Location Drill":
        st.markdown("#### 📍 Single Node Susceptibility Simulation")

        use_existing = st.checkbox("Pre-fill terrain from existing Aizawl node", value=True)

        default_elev = 950.0
        default_slope = 28.0

        if use_existing and not latest_df.empty:
            loc_list = latest_df["location_id"].tolist()
            label_map = {
                r["location_id"]: f"📍 {r.get('location_name', 'Aizawl')} — {r['location_id']}"
                for _, r in latest_df.iterrows()
            }
            chosen_loc = st.selectbox(
                "Select Station Node to Pre-fill:",
                loc_list,
                format_func=lambda x: label_map.get(x, x),
                key="sim_prefill_node"
            )
            node_row = latest_df[latest_df["location_id"] == chosen_loc].iloc[0]
            default_elev = float(node_row["elevation_m"])
            default_slope = float(node_row["slope_deg"])
            loc_name_disp = node_row.get("location_name") or get_location_name(float(node_row["latitude"]), float(node_row["longitude"]))
            st.caption(f"Loaded terrain coordinates: **📍 {loc_name_disp}** | Elevation {default_elev:.0f}m, Slope {default_slope:.1f}°")

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**🏔️ Terrain Parameters**")
            elev_input = st.number_input("Elevation (meters above sea level)", min_value=0.0, max_value=3000.0, value=default_elev, step=25.0)
            slope_input = st.number_input("Slope Gradient (degrees)", min_value=0.0, max_value=85.0, value=default_slope, step=1.0)

        with c2:
            st.markdown("**🌧️ Rainfall Parameters**")
            st.caption(f"Rainy day ≥ {RAINY_DAY_THRESHOLD_MM}mm | Heavy rain ≥ {HEAVY_RAIN_DAY_THRESHOLD_MM}mm")
            rain_input = st.number_input("Simulated Today's Rainfall (mm)", min_value=0.0, max_value=500.0, value=45.0, step=5.0)
            rainy_streak_input = st.number_input("Consecutive Rainy Days (Ending Today)", min_value=0, max_value=60, value=4, step=1)
            heavy_streak_input = st.number_input("Consecutive Heavy Rain Days (Ending Today)", min_value=0, max_value=30, value=1, step=1)

        if st.button("🚀 EXECUTE SIMULATION", type="primary", use_container_width=True, key="exec_single_sim_btn"):
            input_dict = {
                "elevation_m": elev_input,
                "slope_deg": slope_input,
                "rainfall_mm": rain_input,
                "rainfall_1d_mm": rain_input,
                "consecutive_rainy_days": rainy_streak_input,
                "consecutive_heavy_rain_days": heavy_streak_input,
            }
            df_input = pd.DataFrame([input_dict])[features_list]
            prob = float(model.predict_proba(df_input)[:, 1][0])
            risk_label = assign_risk_level(prob)
            is_warning = (prob >= operating_threshold)

            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.markdown("#### 📊 Simulation Outcome")

            r1, r2, r3 = st.columns(3)

            with r1:
                st.markdown(
                    f"""
                    <div class="metric-card {'critical' if is_warning else 'safe'}">
                        <div class="metric-label">Predicted Landslide Probability</div>
                        <div class="metric-value">{prob*100:.1f}%</div>
                        <div class="metric-subtext">Raw Probability: {prob:.4f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with r2:
                st.markdown(
                    f"""
                    <div class="metric-card {risk_label.lower()}">
                        <div class="metric-label">Visual Risk Category</div>
                        <div class="metric-value">{risk_label}</div>
                        <div class="metric-subtext">Operating Threshold: {operating_threshold:.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with r3:
                st.markdown(
                    f"""
                    <div class="metric-card {'critical' if is_warning else 'safe'}">
                        <div class="metric-label">Operational Trigger</div>
                        <div class="metric-value" style="font-size: 1.3rem;">
                            {'🚨 WARNING' if is_warning else '✅ NO WARNING'}
                        </div>
                        <div class="metric-subtext">{'Above threshold' if is_warning else 'Within safe limits'}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    else:
        st.markdown("#### 🗺️ District-Wide Cloudburst & Monsoon Stress-Test")
        st.markdown(
            "Apply a uniform meteorological stress scenario across **all 419 monitoring stations in Aizawl** "
            "to evaluate spatial vulnerability under severe storm conditions."
        )

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            global_rain = st.number_input("Hypothetical Rainfall (mm)", min_value=0.0, max_value=600.0, value=75.0, step=10.0)
        with sc2:
            global_rainy_days = st.number_input("Consecutive Rainy Days", min_value=0, max_value=45, value=5, step=1)
        with sc3:
            global_heavy_days = st.number_input("Consecutive Heavy Rain Days", min_value=0, max_value=20, value=2, step=1)

        if st.button("🌪️ RUN DISTRICT STRESS-TEST", type="primary", use_container_width=True, key="exec_global_sim_btn"):
            sim_df = latest_df[["location_id", "latitude", "longitude", "elevation_m", "slope_deg"]].copy()
            sim_df["rainfall_mm"] = global_rain
            sim_df["rainfall_1d_mm"] = global_rain
            sim_df["consecutive_rainy_days"] = global_rainy_days
            sim_df["consecutive_heavy_rain_days"] = global_heavy_days

            # Enrich with real locality names
            sim_df = enrich_with_location_names(sim_df)

            X_sim = sim_df[features_list]
            sim_probs = model.predict_proba(X_sim)[:, 1]

            sim_df["landslide_probability"] = sim_probs
            sim_df["probability_percent"] = sim_probs * 100
            sim_df["risk_level"] = sim_df["landslide_probability"].apply(assign_risk_level)
            sim_df["is_warning"] = sim_probs >= operating_threshold
            sim_df["warning_status"] = sim_df["is_warning"].map({True: "WARNING", False: "NO_WARNING"})

            total_sim_warnings = int(sim_df["is_warning"].sum())
            critical_count = int((sim_df["risk_level"] == "CRITICAL").sum())
            high_count = int((sim_df["risk_level"] == "HIGH").sum())

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.markdown(f"#### 🚨 Scenario Results: **{total_sim_warnings} / {len(sim_df)} Nodes in WARNING Status**")

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Simulated Warnings", f"{total_sim_warnings:,}")
            k2.metric("Critical Zones", f"{critical_count:,}")
            k3.metric("High Risk Zones", f"{high_count:,}")
            k4.metric("Avg Simulated Probability", f"{sim_probs.mean()*100:.1f}%")

            # Render Simulated Esri Map with Locality Names
            fig_sim = go.Figure()

            for risk in RISK_ORDER:
                sub = sim_df[sim_df["risk_level"] == risk]
                if sub.empty:
                    continue
                fig_sim.add_trace(
                    go.Scattermapbox(
                        lat=sub["latitude"],
                        lon=sub["longitude"],
                        mode="markers",
                        marker=dict(
                            size=[max(8, min(22, p * 22)) for p in sub["landslide_probability"]],
                            color=RISK_COLORS[risk],
                            opacity=0.85,
                        ),
                        name=f"Simulated: {risk}",
                        text=[
                            f"<b>📍 Locality:</b> {r.get('location_name', 'Aizawl')}<br>"
                            f"<b>Node:</b> {r['location_id']}<br>"
                            f"<b>Simulated Prob:</b> {r['landslide_probability']*100:.1f}%<br>"
                            f"<b>Risk:</b> {r['risk_level']}<br>"
                            f"<b>Decision:</b> {r['warning_status']}<br>"
                            f"<b>Elevation:</b> {r['elevation_m']}m | <b>Slope:</b> {r['slope_deg']:.1f}°"
                            for _, r in sub.iterrows()
                        ],
                        hoverinfo="text",
                    )
                )

            center_lat = float(sim_df["latitude"].mean())
            center_lon = float(sim_df["longitude"].mean())

            fig_sim.update_layout(
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
                            "sourceattribution": "Esri Places & Roads",
                            "source": [
                                "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                            ],
                        },
                    ],
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=520,
                paper_bgcolor="#070a12",
                plot_bgcolor="#070a12",
                legend=dict(
                    orientation="h",
                    y=0.01,
                    x=0.01,
                    bgcolor="rgba(11, 15, 25, 0.85)",
                    bordercolor="rgba(255, 255, 255, 0.1)",
                    font=dict(color="#e2e8f0"),
                ),
            )

            st.plotly_chart(fig_sim, use_container_width=True)
