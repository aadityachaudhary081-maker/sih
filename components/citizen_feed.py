"""
NEXORA Command Center — Geo-Tagged Citizen Ground Reporting Component
Includes:
- Direct DOM Injection Device GPS Bridge (Instantaneous coordinate population)
- Fallback Station Dropdown & Manual Inputs
- Real-time Reverse Geocoding via OpenStreetMap Nominatim
- Live satellite map location preview pin
- Spatial Hazard Risk Correlation (Haversine distance to nearest monitoring station)
- Aizawl District jurisdiction verification
"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from citizen_reporting import (
    load_citizen_reports,
    add_citizen_report,
    update_report_status,
    HAZARD_TYPES,
    STATUS_PENDING,
    STATUS_VERIFIED,
    STATUS_RESOLVED,
    STATUS_OPTIONS,
    find_nearest_monitoring_zone,
)
from geocoding import (
    get_location_name,
    format_location_display,
    is_within_mizoram,
)


def cb_reset_to_aizawl():
    """Callback to reset coordinates to central Aizawl."""
    st.session_state["rep_lat_val"] = 23.738800
    st.session_state["rep_lon_val"] = 92.696300
    st.session_state["rep_acc_val"] = 6.5


def render_report_hazard_view(latest_df: pd.DataFrame):
    """Renders the dedicated Report Ground Hazard interactive submission view with instant client GPS resolution."""

    # Ensure baseline coordinate state exists
    if "rep_lat_val" not in st.session_state:
        st.session_state["rep_lat_val"] = 23.738800
    if "rep_lon_val" not in st.session_state:
        st.session_state["rep_lon_val"] = 92.696300
    if "rep_acc_val" not in st.session_state:
        st.session_state["rep_acc_val"] = 6.5

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
        "Upload or capture photograph of the hazard (cracks, debris, runoff, rockfall):",
        type=["jpg", "jpeg", "png"],
        key="dedicated_img_upload",
    )

    # Step 2: Location & GPS Coordinates
    st.markdown("#### 02. Location & GPS Coordinates")
    st.caption("Acquire location via device GPS, select an active station, or enter coordinates manually:")

    loc_mode = st.radio(
        "Location Mode",
        ["📡 Device GPS (Browser)", "🛰️ Select Monitored Station", "✍️ Manual Coordinate Entry"],
        horizontal=True,
        key="loc_input_mode_radio",
    )

    if loc_mode == "📡 Device GPS (Browser)":
        # Embedded Client-Side HTML5 Geolocation Bridge using direct DOM value injection
        components.html(
            """
            <div style="display: flex; align-items: center; gap: 12px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <button id="gps-btn" onclick="fetchDeviceLocation()" style="
                    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
                    color: #ffffff;
                    border: 1px solid #38bdf8;
                    padding: 8px 18px;
                    border-radius: 6px;
                    font-size: 0.85rem;
                    font-weight: 700;
                    cursor: pointer;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;">
                    📍 Request Device GPS Location
                </button>
                <span id="gps-status" style="font-size: 0.8rem; color: #94a3b8;">Click button to auto-fill input boxes</span>
            </div>
            <script>
            function setNativeValue(element, value) {
                const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
                const prototype = Object.getPrototypeOf(element);
                const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                
                if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
                    prototypeValueSetter.call(element, value);
                } else {
                    valueSetter.call(element, value);
                }
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
            }

            function fetchDeviceLocation() {
                const status = document.getElementById('gps-status');
                const btn = document.getElementById('gps-btn');
                
                if (!navigator.geolocation) {
                    status.innerHTML = "<span style='color: #f87171;'>Browser does not support Geolocation.</span>";
                    return;
                }
                
                btn.disabled = true;
                status.innerHTML = "<span style='color: #38bdf8;'>Querying GPS sensors...</span>";
                
                navigator.geolocation.getCurrentPosition(
                    function(pos) {
                        const lat = pos.coords.latitude.toFixed(6);
                        const lon = pos.coords.longitude.toFixed(6);
                        const acc = pos.coords.accuracy.toFixed(1);
                        
                        try {
                            const doc = window.parent.document;
                            const inputs = doc.querySelectorAll('input[type="number"]');
                            
                            if (inputs.length >= 3) {
                                setNativeValue(inputs[0], lat);
                                setNativeValue(inputs[1], lon);
                                setNativeValue(inputs[2], acc);
                                status.innerHTML = `<span style='color: #34d399;'>Filled: ${lat}, ${lon} (±${acc}m)</span>`;
                            } else {
                                status.innerHTML = "<span style='color: #f59e0b;'>Input elements not detected.</span>";
                            }
                        } catch (e) {
                            status.innerHTML = `<span style='color: #f87171;'>DOM Access Blocked: ${e.message}</span>`;
                        }
                        btn.disabled = false;
                    },
                    function(err) {
                        btn.disabled = false;
                        let msg = "Permission denied or unavailable.";
                        if (err.code === 1) msg = "Location permission blocked in browser.";
                        else if (err.code === 2) msg = "Position unavailable.";
                        else if (err.code === 3) msg = "Request timed out.";
                        status.innerHTML = `<span style='color: #f87171;'>${msg} Switch to 'Select Monitored Station'.</span>`;
                    },
                    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                );
            }
            </script>
            """,
            height=46,
        )

    elif loc_mode == "🛰️ Select Monitored Station":
        if not latest_df.empty and "location_id" in latest_df.columns:
            station_list = sorted(latest_df["location_id"].unique())
            selected_st = st.selectbox(
                "Select Verified Aizawl Grid Station:",
                station_list,
                key="sb_station_picker",
            )
            matched_row = latest_df[latest_df["location_id"] == selected_st].iloc[0]
            st.session_state["rep_lat_val"] = float(matched_row["latitude"])
            st.session_state["rep_lon_val"] = float(matched_row["longitude"])
            st.session_state["rep_acc_val"] = 5.0
            st.caption(f"Selected: **{selected_st}** — Risk Tier: **{matched_row.get('risk_level', 'N/A')}** | Elev: **{matched_row.get('elevation_m', 0):.0f}m**")
        else:
            st.info("No active station records found in memory.")

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Coordinate Display & Manual Inputs
    c_lat, c_lon, c_acc = st.columns(3)

    with c_lat:
        rep_lat = st.number_input(
            "Latitude (°N)",
            min_value=-90.0,
            max_value=90.0,
            value=float(st.session_state["rep_lat_val"]),
            format="%.6f",
            key="rep_lat_num_input",
            disabled=(loc_mode == "🛰️ Select Monitored Station"),
        )
    with c_lon:
        rep_lon = st.number_input(
            "Longitude (°E)",
            min_value=-180.0,
            max_value=180.0,
            value=float(st.session_state["rep_lon_val"]),
            format="%.6f",
            key="rep_lon_num_input",
            disabled=(loc_mode == "🛰️ Select Monitored Station"),
        )
    with c_acc:
        rep_acc = st.number_input(
            "Estimated Accuracy (± meters)",
            min_value=0.1,
            max_value=10000.0,
            value=float(st.session_state["rep_acc_val"]),
            format="%.1f",
            key="rep_acc_num_input",
            disabled=(loc_mode == "🛰️ Select Monitored Station"),
        )

    st.session_state["rep_lat_val"] = rep_lat
    st.session_state["rep_lon_val"] = rep_lon
    st.session_state["rep_acc_val"] = rep_acc

    # Real-time API locality lookup for entered coordinates via OpenStreetMap Nominatim
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
        status_badge_html = '<span style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; padding: 2px 8px; border-radius: 4px; font-size: 0.68rem; font-weight: 800; margin-left: 8px;">🚫 OUTSIDE DISTRICT BOUNDARY</span>'
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

    # Satellite Map Location Preview Pin
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
                zoom=12.5,
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
            height=220,
            paper_bgcolor="#070a12",
            plot_bgcolor="#070a12",
        )
        st.plotly_chart(fig_preview, width="stretch")

    # Boundary Alert
    if not is_in_district:
        st.markdown(
            f"""
            <div style="background: rgba(239, 68, 68, 0.16); border: 2px solid #ef4444; border-radius: 10px; padding: 16px 20px; margin: 12px 0 16px 0; box-shadow: 0 0 24px rgba(239, 68, 68, 0.25);">
                <div style="display: flex; align-items: flex-start; gap: 14px;">
                    <span style="font-size: 1.8rem; line-height: 1;">🚫</span>
                    <div style="flex: 1;">
                        <div style="font-size: 1.05rem; font-weight: 800; color: #f87171; letter-spacing: -0.01em;">
                            LOCATION OUTSIDE DISTRICT JURISDICTION — ENTRY BLOCKED
                        </div>
                        <div style="font-size: 0.85rem; color: #fecaca; margin-top: 5px; line-height: 1.55;">
                            Detected coordinates <strong>({coord_str})</strong> resolve to <strong style="color: #ffffff;">{display_title}</strong>, which is outside the active <strong>Aizawl District &amp; Mizoram State</strong> disaster monitoring perimeter.<br>
                            If testing outside Mizoram, switch to <strong>'🛰️ Select Monitored Station'</strong> above or click <strong>Reset to Aizawl Grid</strong> below.
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c_rst1, c_rst2 = st.columns([3, 1])
        with c_rst1:
            st.caption("To enable reporting, reset coordinates to the Aizawl monitoring grid:")
        with c_rst2:
            st.button("📍 Reset to Aizawl Grid", key="btn_reset_to_aizawl", on_click=cb_reset_to_aizawl, width="stretch")

    # Step 3: Hazard details & Submit
    st.markdown("#### 03. Hazard Classification & Details")

    with st.form("dedicated_citizen_report_form"):
        c_type, c_desc = st.columns([1, 2])

        with c_type:
            rep_type = st.selectbox(
                "Hazard Observation Type:",
                HAZARD_TYPES,
                index=2,
                key="rep_type_sel",
                disabled=not is_in_district,
            )
        with c_desc:
            rep_desc = st.text_area(
                "Describe the observed hazard:",
                placeholder="E.g. Visible 2-inch road cracking across asphalt slope, active water seep near foundation..." if is_in_district else "🚫 Entry disabled: Coordinates are outside Aizawl District jurisdiction.",
                height=90,
                key="rep_desc_txt",
                disabled=not is_in_district,
            )

        if not is_in_district:
            submit_btn = st.form_submit_button("🚫 SUBMISSION BLOCKED — LOCATION OUTSIDE DISTRICT", disabled=True, width="stretch")
        else:
            submit_btn = st.form_submit_button("🚨 TRANSMIT GEOTAGGED GROUND REPORT", type="primary", width="stretch")

        if submit_btn:
            if not is_in_district:
                st.error("🚫 Location outside district / state boundary. Ground hazard report not allowed.")
            elif not rep_desc.strip():
                st.error("Please provide a brief description of the observed hazard.")
            else:
                new_report = add_citizen_report(
                    image_file=uploaded_image,
                    latitude=rep_lat,
                    longitude=rep_lon,
                    gps_accuracy_m=rep_acc,
                    report_type=rep_type,
                    description=rep_desc,
                    latest_risk_df=latest_df,
                )

                nearest_zone_name = ""
                if new_report.get("nearest_zone_id"):
                    matched_row = latest_df[latest_df["location_id"] == new_report["nearest_zone_id"]]
                    if not matched_row.empty:
                        nearest_zone_name = get_location_name(float(matched_row.iloc[0]["latitude"]), float(matched_row.iloc[0]["longitude"]), use_api=True)

                final_report_loc = display_title if has_named_location else coord_str

                st.success("✅ Ground Hazard Report successfully registered, geotagged, and correlated!")
                st.markdown(
                    f"""
                    <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 10px; padding: 16px 20px; margin: 14px 0;">
                        <div style="font-weight: 800; color: #34d399; font-size: 1.1rem;">INCIDENT LOGGED: {new_report['id']}</div>
                        <div style="font-size: 0.85rem; color: #f1f5f9; margin-top: 6px; line-height: 1.6;">
                            • <strong>Locality:</strong> 📍 {final_report_loc} ({coord_str})<br>
                            • <strong>Hazard Type:</strong> {new_report['report_type']}<br>
                            • <strong>Nearest Monitored Station:</strong> <span style="color: #38bdf8;">{new_report['nearest_zone_id']}</span> {f'({nearest_zone_name})' if nearest_zone_name else ''} — <strong>{new_report['distance_to_zone_m']} m away</strong><br>
                            • <strong>Station Risk Status:</strong> <strong style="color: #f97316;">{new_report['zone_risk_level']}</strong> (Prob: {new_report['zone_probability']*100:.1f}%)<br>
                            • <strong>Verification Status:</strong> <strong style="color: #f59e0b;">{new_report['status']}</strong>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_citizen_feed(latest_df: pd.DataFrame):
    """Renders the Citizen Ground Reporting management feed and submission interface."""
    render_report_hazard_view(latest_df)
