"""
NEXORA Command Center — Right-Side Hamburger Control Panel Component
Provides sliding emergency dispatch, telemetry shortcuts, and rapid actions.
"""

import streamlit as st


def render_right_drawer(risk_summary: dict, data_mode: str):
    """Renders the slide-over quick-control drawer when toggled."""
    if not st.session_state.get("drawer_open", False):
        return

    warnings_count = int(risk_summary.get("warnings", 0))

    st.markdown(
        f"""
        <div class="right-drawer-container">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 10px; margin-bottom: 14px;">
                <div style="font-weight: 800; font-size: 1.05rem; color: #38bdf8; display: flex; align-items: center; gap: 8px;">
                    ⚡ COMMAND QUICK-DISPATCH &amp; EMERGENCY PANEL
                </div>
            </div>
            <div style="font-size: 0.78rem; color: #cbd5e1; margin-bottom: 14px;">
                Direct emergency hotlines and rapid response protocols for Aizawl District disaster management.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    d_col1, d_col2, d_col3 = st.columns([1, 1, 1])
    with d_col1:
        if st.button("✕ CLOSE CONTROL PANEL", key="close_drawer_btn", use_container_width=True):
            st.session_state["drawer_open"] = False
            st.rerun()
    with d_col2:
        if st.button("🚨 REPORT GROUND HAZARD", type="primary", key="drawer_report_hazard_btn", use_container_width=True):
            st.session_state["active_nav"] = "🚨 Report Ground Hazard"
            st.session_state["drawer_open"] = False
            st.rerun()
    with d_col3:
        if st.button("🔄 FORCE TELEMETRY SYNC", key="drawer_refresh_cache_btn", use_container_width=True):
            st.cache_data.clear()
            st.success("Telemetry cache cleared and refreshed.")
            st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Emergency Helplines Grid
    st.markdown("#### 📞 District Emergency Helplines & SOS Dispatch")

    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(
            """
            <div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #f87171; font-weight: 700; text-transform: uppercase;">MSDMA STATE CONTROL ROOM</div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #f8fafc; font-family: 'JetBrains Mono', monospace; margin-top: 4px;">1070 (Toll-Free)</div>
                <div style="font-size: 0.72rem; color: #94a3b8;">Direct Line: 0389-2334057</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            """
            <div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(249, 115, 22, 0.35); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #fb923c; font-weight: 700; text-transform: uppercase;">AIZAWL DC EMERGENCY CELL</div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #f8fafc; font-family: 'JetBrains Mono', monospace; margin-top: 4px;">0389-2322238</div>
                <div style="font-size: 0.72rem; color: #94a3b8;">DDMA Duty Officer: 0389-2316885</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h3:
        st.markdown(
            """
            <div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;">SDRF / POLICE RAPID DISPATCH</div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #f8fafc; font-family: 'JetBrains Mono', monospace; margin-top: 4px;">112 / 101</div>
                <div style="font-size: 0.72rem; color: #94a3b8;">Search &amp; Rescue Cell: 0389-2334307</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border: none; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 16px 0 10px 0;'>", unsafe_allow_html=True)
