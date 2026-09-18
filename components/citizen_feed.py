"""
NEXORA Command Center — Geo-Tagged Citizen Ground Reporting Component
Includes:
- Instant Location Presets (Surat Test, Aizawl Center, Monitored Stations)
- Device Browser GPS Bridge with automatic sync
- Dynamic Map Re-centering & Satellite Pinning
- Spatial Hazard Risk Correlation
- District Boundary Guard with Simulation Override for Testing
"""

from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from citizen_reporting import add_citizen_report, HAZARD_TYPES
from geocoding import get_location_name, is_within_mizoram

def set_coords(lat: float, lon: float, acc: float = 5.0):
    """Safely updates session state for coordinates. Immediately syncs the map."""
    st.session_state.rep_lat = float(lat)
    st.session_state.rep_lon = float(lon)
    st.session_state.rep_acc = float(acc)


def render_report_hazard_view(latest_df: pd.DataFrame):
    """Renders the dedicated Report Ground Hazard interactive submission view."""

    # 1. Catch GPS parameters passed from the browser component
    if "gps_lat" in st.query_params and "gps_lon" in st.query_params:
        try:
            st.session_state.rep_lat = float(st.query_params["gps_lat"])
            st.session_state.rep_lon = float(st.query_params["gps_lon"])
            st.session_state.rep_acc = float(st.query_params.get("gps_acc", 10.0))
            st.query_params.clear()
            st.toast("📍 Real GPS coordinates synced with map!", icon="✅")
        except Exception:
            pass

    # 2. Ensure baseline coordinate state exists
    if "rep_lat" not in st.session_state:
        st.session_state.rep_lat = 23.738800
    if "rep_lon" not in st.session_state:
        st.session_state.rep_lon = 92.696300
    if "rep_acc" not in st.session_state:
        st.session_state.rep_acc = 6.5

    col_t1, col_t2 = st.columns([4, 1])

    with col_t1:
        st.markdown(
            """
            <div class="command-panel" style="margin-bottom: 14px;">
                <div class="panel-header">
                    <div class="panel-title">🚨 GEOTAGGED CITIZEN GROUND HAZARD REPORTING</div>
                    <div style="font-size: 0.72rem; color: #38bdf8; font-family: 'JetBrains Mono', monospace;">
                        EMERGENCY CROWDSOURCING &amp; FIELD EVIDENCE INGESTION
                    </div>
                </div>
                <div style="font-size: 0.8rem; color: #cbd5e1;">
                    Observed active tensile road cracks, rockfalls, mud displacement, retaining wall failure, or drainage overflow?
                    Submit geotagged photographic evidence to correlate with risk models and alert district emergency responders.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_t2:
        if st.button("⬅️ Return to Overview", width="stretch"):
            st.session_state["active_nav"] = "◉ Command Overview"
            st.rerun()

    # Step 1: Photographic evidence
    st.markdown("#### 01. Photographic Evidence")
    uploaded_image = st.file_uploader(
        "Upload or capture photograph of the hazard:",
        type=["jpg", "jpeg", "png"],
        key="dedicated_img_upload",
    )

    # Step 2: Location & GPS Coordinates
    st.markdown("#### 02. Location & GPS Coordinates")
    st.caption("Choose an acquisition mode below:")

    loc_mode = st.radio(
        "Location Mode",
        [
            "🛰️ Monitored Station (Aizawl Grid)",
            "📍 Instant Presets (Surat / Aizawl)",
            "📡 Device GPS (Browser)",
            "✍️ Manual Coordinate Entry",
        ],
        horizontal=True,
        key="loc_input_mode_radio",
    )

    if loc_mode == "🛰️ Monitored Station (Aizawl Grid)":
        if not latest_df.empty and "location_id" in latest_df.columns:
            station_list = sorted(latest_df["location_id"].unique())
            selected_st = st.selectbox(
                "Select Verified Aizawl Grid Station:",
                station_list,
                key="sb_station_picker",
            )
            matched_row = latest_df[latest_df["location_id"] == selected_st].iloc[0]
            set_coords(matched_row["latitude"], matched_row["longitude"], 5.0)
            st.caption(f"Selected: **{selected_st}** — Elev: **{matched_row.get('elevation_m', 0):.0f}m**")

    elif loc_mode == "📍 Instant Presets (Surat / Aizawl)":
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            if st.button("📍 Set to Surat", width="stretch"):
                set_coords(21.170240, 72.831060, 8.0)
        with p_col2:
            if st.button("📍 Set to Aizawl Center", width="stretch"):
                set_coords(23.738800, 92.696300, 5.0)
        with p_col3:
            if st.button("📍 Set to High Risk Zone", width="stretch"):
                set_coords(23.772500, 92.724100, 5.0)

    elif loc_mode == "📡 Device GPS (Browser)":
        components.html(
            """
            <div style="display: flex; align-items: center; gap: 12px; font-family: sans-serif;">
                <button id="gps-btn" onclick="fetchDeviceLocation()" style="
                    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
                    color: #ffffff;
                    border: 1px solid #38bdf8;
                    padding: 8px 18px;
                    border-radius: 6px;
                    font-size: 0.85rem;
                    font-weight: 700;
                    cursor: pointer;">
                    📍 Request Device GPS
                </button>
                <span id="gps-status" style="font-size: 0.8rem; color: #94a3b8;">Click button to request sensor coordinates</span>
            </div>
            <script>
            function fetchDeviceLocation() {
                const status = document.getElementById('gps-status');
                const btn = document.getElementById('gps-btn');
                if (!navigator.geolocation) {
                    status.innerHTML = "<span style='color: #f87171;'>Browser does not support Geolocation.</span>";
                    return;
                }
                btn.disabled = true;
                status.innerHTML = "<span style='color: #38bdf8;'>Detecting GPS coordinates...</span>";
                navigator.geolocation.getCurrentPosition(
                    function(pos) {
                        const lat = pos.coords.latitude.toFixed(6);
                        const lon = pos.coords.longitude.toFixed(6);
                        const acc = pos.coords.accuracy.toFixed(1);
                        status.innerHTML = `<span style='color: #34d399;'>Found: ${lat}, ${lon}. Syncing...</span>`;
                        const targetUrl = new URL(window.parent.location.href);
                        targetUrl.searchParams.set('gps_lat', lat);
                        targetUrl.searchParams.set('gps_lon', lon);
                        targetUrl.searchParams.set('gps_acc', acc);
                        window.parent.location.href = targetUrl.toString();
                    },
                    function(err) {
                        btn.disabled = false;
                        status.innerHTML = `<span style='color: #f87171;'>Permission blocked. Use 'Instant Presets'.</span>`;
                    },
                    { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
                );
            }
            </script>
            """,
            height=46,
        )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 3. Streamlit Native State-Bound Inputs (No 'value=' param, mapped directly to session_state)
    c_lat, c_lon, c_acc = st.columns(3)

    with c_lat:
        rep_lat = st.number_input(
            "Latitude (°N)",
            min_value=-90.0,
            max_value=90.0,
            format="%.6f",
            key="rep_lat",
            disabled=(loc_mode == "🛰️ Monitored Station (Aizawl Grid)"),
        )
    with c_lon:
        rep_lon = st.number_input(
            "Longitude (°E)",
            min_value=-180.0,
            max_value=180.0,
            format="%.6f",
            key="rep_lon",
            disabled=(loc_mode == "🛰️ Monitored Station (Aizawl Grid)"),
        )
    with c_acc:
        rep_acc = st.number_input(
            "Estimated Accuracy (± meters)",
            min_value=0.1,
            max_value=10000.0,
            format="%.1f",
            key="rep_acc",
            disabled=(loc_mode == "🛰️ Monitored Station (Aizawl Grid)"),
        )

    # 4. Reverse Geocoding via OpenStreetMap Nominatim
    loc_name_api = get_location_name(rep_lat, rep_lon, use_api=True)
    coord_str = f"{rep_lat:.6f}° N, {rep_lon:.6f}° E"
    is_in_district = is_within_mizoram(rep_lat, rep_lon, loc_name_api)

    has_named_location = bool(loc_name_api and not any(deg in loc_name_api for deg in ["°", "°N", "°E", "° N", "° E"]))
    display_title = loc_name_api if has_named_location else coord_str
    sub_info = f"COORDINATES: {coord_str} (Accuracy: ±{rep_acc:.1f}m)"

    if is_in_district:
        status_badge_html = '<span style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; padding: 2px 8px; border-radius: 4px; font-size: 0.68rem; font-weight: 800; margin-left: 8px;">✓ WITHIN MONITORING GRID</span>'
        card_style = "background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(56, 189, 248, 0.35);"
    else:
        status_badge_html = '<span style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; padding: 2px 8px; border-radius: 4px; font-size: 0.68rem; font-weight: 800; margin-left: 8px;">🚫 OUTSIDE BOUNDARY</span>'
        card_style = "background: rgba(30, 15, 20, 0.9); border: 1px solid rgba(239, 68, 68, 0.6);"

    st.markdown(
        f"""
        <div style="{card_style} border-radius: 8px; padding: 12px 16px; margin: 10px 0 14px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">
                    ONLINE REVERSE GEOCODED LOCALITY (OpenStreetMap):
                </div>
                <div>{status_badge_html}</div>
            </div>
            <div style="font-size: 1.15rem; font-weight: 800; color: {'#38bdf8' if is_in_district else '#f87171'}; margin-top: 3px;">
                📍 {display_title}
            </div>
            <div style="font-size: 0.75rem; color: #64748b; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">
                {sub_info}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. Satellite Map Location Preview Pin (Dynamic Key forces immediate recentering)
    with st.expander("🗺️ Preview Selected Location on Satellite Map", expanded=True):
        fig_preview = go.Figure()
        fig_preview.add_trace(
            go.Scattermapbox(
                lat=[rep_lat],
                lon=[rep_lon],
                mode="markers+text",
                marker=dict(size=18, color="#ef4444"),
                text=["📍 REPORT PIN"],
                textposition="top right",
                textfont=dict(size=11, color="#ffffff"),
                hovertext=f"<b>Report Location:</b><br>{display_title}<br>{coord_str}",
                hoverinfo="text",
            )
        )
        fig_preview.update_layout(
            mapbox=dict(
                style="white-bg",
                center=dict(lat=rep_lat, lon=rep_lon),
                zoom=12.0,
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
                        "sourceattribution": "Esri Reference Places",
                        "source": [
                            "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                        ],
                    },
                ],
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=240,
            paper_bgcolor="#070a12",
            plot_bgcolor="#070a12",
        )
        st.plotly_chart(fig_preview, width="stretch", key=f"preview_map_{rep_lat:.4f}_{rep_lon:.4f}")

    # Boundary Alert
    if not is_in_district:
        st.markdown(
            f"""
            <div style="background: rgba(239, 68, 68, 0.16); border: 2px solid #ef4444; border-radius: 10px; padding: 16px 20px; margin: 12px 0 16px 0;">
                <div style="display: flex; align-items: flex-start; gap: 14px;">
                    <span style="font-size: 1.8rem; line-height: 1;">🚫</span>
                    <div style="flex: 1;">
                        <div style="font-size: 1.05rem; font-weight: 800; color: #f87171;">
                            LOCATION OUTSIDE DISTRICT JURISDICTION — ENTRY BLOCKED
                        </div>
                        <div style="font-size: 0.85rem; color: #fecaca; margin-top: 5px; line-height: 1.55;">
                            Detected coordinates resolve to <strong style="color: #ffffff;">{display_title}</strong>, which is outside the active monitoring boundary.<br>
                            To test reporting, select <strong>'🛰️ Monitored Station'</strong> or choose an <strong>Aizawl Preset</strong> above.
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Step 3: Hazard details & Submit
    st.markdown("#### 03. Hazard Classification & Details")

    with st.form("dedicated_citizen_report_form"):
        c_type, c_desc = st.columns([1, 2])

        with c_type:
            rep_type = st.selectbox(
                "Hazard Observation Type:",
                HAZARD_TYPES,
                index=2,
                disabled=not is_in_district,
            )
        with c_desc:
            rep_desc = st.text_area(
                "Describe the observed hazard:",
                placeholder="E.g. Visible 2-inch road cracking..." if is_in_district else "🚫 Entry disabled.",
                height=90,
                disabled=not is_in_district,
            )

        if not is_in_district:
            submit_btn = st.form_submit_button("🚫 SUBMISSION BLOCKED — LOCATION OUTSIDE DISTRICT", disabled=True, width="stretch")
        else:
            submit_btn = st.form_submit_button("🚨 TRANSMIT GEOTAGGED GROUND REPORT", type="primary", width="stretch")

        if submit_btn and is_in_district and rep_desc.strip():
            new_report = add_citizen_report(
                image_file=uploaded_image,
                latitude=rep_lat,
                longitude=rep_lon,
                gps_accuracy_m=rep_acc,
                report_type=rep_type,
                description=rep_desc,
                latest_risk_df=latest_df,
            )
            st.success("✅ Ground Hazard Report successfully registered!")


def render_citizen_feed(latest_df: pd.DataFrame):
    """Renders the Citizen Ground Reporting management feed and submission interface."""
    render_report_hazard_view(latest_df)
