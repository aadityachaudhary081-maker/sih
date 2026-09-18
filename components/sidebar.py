"""
NEXORA Command Center — Sidebar Navigation Component
"""

import streamlit as st


def render_sidebar():
    """Renders the dark command center sidebar and returns selected active page and mode."""
    if "active_nav" not in st.session_state:
        st.session_state["active_nav"] = "◉ Command Overview"

    nav_options = [
        "◉ Command Overview",
        "🗺️ Live GIS Risk Map",
        "📍 Location Intelligence",
        "🧠 Risk Engine",
        "🧪 What-if Simulation",
        "🌧️ Rainfall Intelligence",
        "🚨 Early Warning Center",
        "📊 Analytics & Distribution",
        "⚙️ System Health",
    ]

    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 10px 4px 16px 4px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 14px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="background: linear-gradient(135deg, #0284c7, #38bdf8); width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; box-shadow: 0 0 12px rgba(56, 189, 248, 0.4);">
                        🌐
                    </div>
                    <div>
                        <div style="font-weight: 800; font-size: 1.15rem; letter-spacing: 0.08em; color: #f8fafc;">NEXORA</div>
                        <div style="font-size: 0.68rem; color: #38bdf8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em;">DISASTER INTELLIGENCE</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Mode Selection Switcher
        st.markdown("<div style='font-size: 0.72rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;'>OPERATING MODE</div>", unsafe_allow_html=True)
        data_mode = st.radio(
            "System Data Mode",
            ["● Live Monitoring", "🧪 What-if Simulation"],
            index=0,
            label_visibility="collapsed",
            key="global_data_mode"
        )
        mode_clean = "Live Monitoring" if "Live" in data_mode else "What-if Simulation"

        st.markdown("<hr style='border: none; border-top: 1px solid rgba(255, 255, 255, 0.06); margin: 12px 0;'>", unsafe_allow_html=True)

        # Main Navigation
        st.markdown("<div style='font-size: 0.72rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;'>COMMAND NAVIGATION</div>", unsafe_allow_html=True)

        current_active = st.session_state.get("active_nav", "◉ Command Overview")
        default_index = nav_options.index(current_active) if current_active in nav_options else 0

        def on_nav_change():
            st.session_state["active_nav"] = st.session_state["nav_radio_value"]

        st.radio(
            "Navigation",
            nav_options,
            index=default_index,
            label_visibility="collapsed",
            key="nav_radio_value",
            on_change=on_nav_change,
        )

        st.markdown("<hr style='border: none; border-top: 1px solid rgba(255, 255, 255, 0.06); margin: 14px 0 12px 0;'>", unsafe_allow_html=True)

        # Citizen Ground Hazard Action CTA
        st.markdown(
            """
            <div style="background: rgba(56, 189, 248, 0.06); border: 1px dashed rgba(56, 189, 248, 0.3); border-radius: 10px; padding: 10px; margin-bottom: 12px;">
                <div style="font-size: 0.72rem; font-weight: 700; color: #38bdf8; margin-bottom: 2px;">CROWDSOURCED GROUND HAZARD</div>
                <div style="font-size: 0.68rem; color: #94a3b8; line-height: 1.3;">
                    Geotag active cracks, rockfalls, or slope displacement.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🚨 REPORT GROUND HAZARD", type="primary", use_container_width=True, key="sidebar_report_hazard_btn"):
            st.session_state["active_nav"] = "🚨 Report Ground Hazard"
            st.rerun()

        st.markdown(
            """
            <div style="margin-top: 20px; padding: 8px 10px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.68rem; color: #64748b;">
                <div><strong>REGION:</strong> Aizawl District, MZ</div>
                <div><strong>GRID NODES:</strong> 419 Location Points</div>
                <div><strong>MODEL:</strong> Random Forest v1.6</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state.get("active_nav", "◉ Command Overview"), mode_clean
