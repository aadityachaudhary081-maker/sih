"""
NEXORA Command Center — Top Header Component with Hamburger Control Panel
"""

from datetime import datetime

import streamlit as st


def render_header(risk_summary: dict, data_mode: str = "Live Monitoring"):
    """Renders the top command center header with live system telemetry, hamburger drawer button, and rapid action trigger."""
    timestamp_raw = risk_summary.get("prediction_timestamp_utc")
    if timestamp_raw:
        try:
            dt = datetime.fromisoformat(timestamp_raw)
            formatted_time = dt.strftime("%d %b %Y • %H:%M UTC")
        except Exception:
            formatted_time = str(timestamp_raw)
    else:
        formatted_time = datetime.now().strftime("%d %b %Y • %H:%M IST")

    is_live = (data_mode == "Live Monitoring")

    badge_html = (
        '<span class="nexora-live-badge"><span class="nexora-pulse-dot"></span> PIPELINE ONLINE</span>'
        if is_live else
        '<span class="nexora-live-badge" style="background: rgba(168,85,247,0.15); border-color: rgba(168,85,247,0.4); color: #c084fc;">🧪 WHAT-IF SIMULATION</span>'
    )

    col1, col2, col3 = st.columns([4.2, 1.4, 1.4])

    with col1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 2.2rem;">🛰️</div>
                <div>
                    <div class="nexora-brand-title">
                        BHUPULSE <span style="font-size: 0.85rem; font-weight: 500; color: #94a3b8; letter-spacing: 0.05em;">| DISASTER INTELLIGENCE CENTER</span>
                    </div>
                    <div class="nexora-brand-subtitle">
                        sense. predict. protect
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div style="display: flex; flex-direction: column; align-items: flex-end; justify-content: center; height: 100%;">
                <div style="margin-bottom: 2px;">
                    {badge_html}
                </div>
                <div style="font-size: 0.68rem; color: #64748b; font-family: 'JetBrains Mono', monospace;">
                    UPDATED: <strong style="color: #cbd5e1;">{formatted_time}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        # Hamburger & Report Hazard buttons
        btn_h1, btn_h2 = st.columns([1, 1])
        with btn_h1:
            if st.button("🚨 Report", key="header_report_hazard_btn", type="primary", use_container_width=True):
                st.session_state["active_nav"] = "🚨 Report Ground Hazard"
                st.rerun()
        with btn_h2:
            is_open = st.session_state.get("drawer_open", False)
            btn_label = "✕ Close" if is_open else "☰ Menu"
            if st.button(btn_label, key="header_hamburger_btn", use_container_width=True):
                st.session_state["drawer_open"] = not is_open
                st.rerun()

    st.markdown("<hr style='border: none; border-top: 1px solid rgba(255, 255, 255, 0.07); margin: 10px 0 16px 0;'>", unsafe_allow_html=True)
