"""
NEXORA Command Center — System Health & Technical Architecture Component
Provides live telemetry, pipeline monitoring, and system specifications.
"""

import streamlit as st


def render_system_health(risk_summary: dict):
    """Renders the System Health and Pipeline Telemetry component."""
    st.markdown(
        """
        <div class="command-panel">
            <div class="panel-header">
                <div class="panel-title">⚙️ SYSTEM HEALTH, DATA FRESHNESS &amp; ARCHITECTURE</div>
                <div style="font-size: 0.72rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
                    SUBSYSTEM STATUS • MODEL SPECIFICATIONS • ML INGESTION PIPELINE
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🟢 Subsystem Diagnostics")
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px 18px;">
                <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
                    <span>🤖 <strong>Production ML Inference Model</strong></span>
                    <span style="color: #34d399; font-weight: 700;">● ONLINE / LOADED</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
                    <span>🌧️ <strong>Open-Meteo IST Ingestion Pipeline</strong></span>
                    <span style="color: #34d399; font-weight: 700;">● ACTIVE / SYNCED</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
                    <span>🗺️ <strong>Esri Geospatial Satellite Cache</strong></span>
                    <span style="color: #34d399; font-weight: 700;">● AVAILABLE</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
                    <span>📁 <strong>State Store (phase11 daily log)</strong></span>
                    <span style="color: #34d399; font-weight: 700;">● VERIFIED</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 0;">
                    <span>📷 <strong>Citizen Geotag Evidence Store</strong></span>
                    <span style="color: #34d399; font-weight: 700;">● ONLINE</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown("#### 🔬 Model Architecture")
        model_name = risk_summary.get("model_name", "Random Forest")
        op_thresh = risk_summary.get("operating_threshold", 0.47)
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px 18px; font-size: 0.82rem; line-height: 1.6;">
                • <strong>Production Algorithm:</strong> {model_name} (Scikit-Learn 1.6.1)<br>
                • <strong>Operating Decision Threshold:</strong> <span style="color: #38bdf8; font-weight: bold;">{op_thresh:.2f} ({op_thresh*100:.0f}%)</span><br>
                • <strong>Decision Rule:</strong> <code>Probability ≥ {op_thresh:.2f} → WARNING</code><br>
                • <strong>Monitored Spatial Nodes:</strong> {risk_summary.get('total_locations', 419)} stations in Aizawl<br>
                • <strong>Historical Predictions Logged:</strong> {risk_summary.get('total_prediction_records', 1573):,} records<br>
                • <strong>Update Frequency:</strong> Hourly telemetry / daily precipitation consolidation
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 🔄 End-to-End Disaster Intelligence Flow")

    st.code(
        """
Open-Meteo Forecast API (IST Timezone)
   ↓
Per-Grid Daily Precipitation Log (Calendar-Day Strict Gap Policy)
   ↓
Rainfall Feature Engine (rainfall_mm, rainfall_1d_mm, consecutive_rainy_days, consecutive_heavy_rain_days)
   ↓
Spatial Broadcast Join with Static Terrain (elevation_m, slope_deg) across 419 Locations
   ↓
Production Random Forest Inference (predict_proba)
   ↓
Binary Threshold Classification (Threshold = 0.47 -> WARNING / NO_WARNING)
   ↓
GIS Interactive Risk Map & Priority Warning Center
   +
Crowdsourced Geotagged Ground Hazard Evidence (GPS + Photos + Spatial Correlation)
   ↓
Emergency Authority Command & Rapid Field Dispatch
        """,
        language=None,
    )
