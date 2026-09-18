"""
NEXORA Command Center — Design System & Custom Styles
Includes:
- Dark charcoal / military command-center palette
- Right-side slide-over hamburger drawer with cubic-bezier transition
- Locality name badges & glowing status telemetry
- Glassmorphism cards, modern buttons, and risk highlights
"""

COMMAND_CENTER_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* Base Command Center Theme */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background-color: #070a12 !important;
    color: #e2e8f0 !important;
}

/* Hide default streamlit header decoration bar */
header[data-testid="stHeader"] {
    background: rgba(7, 10, 18, 0.9) !important;
    backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #090d16;
}
::-webkit-scrollbar-thumb {
    background: #1e293b;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: #38bdf8;
}

/* Command Center Top Header */
.nexora-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(11, 15, 25, 0.98));
    border: 1px solid rgba(56, 189, 248, 0.18);
    border-radius: 12px;
    padding: 14px 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.nexora-brand-title {
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    background: linear-gradient(90deg, #38bdf8, #818cf8, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: flex;
    align-items: center;
    gap: 8px;
}

.nexora-brand-subtitle {
    font-size: 0.72rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 2px;
    font-weight: 600;
}

.nexora-live-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.nexora-pulse-dot {
    width: 7px;
    height: 7px;
    background-color: #10b981;
    border-radius: 50%;
    box-shadow: 0 0 8px #10b981;
    animation: nexora-pulse 2s infinite ease-in-out;
}

@keyframes nexora-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(1.3); }
}

/* Locality Tag / Location Name Pill */
.locality-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: #38bdf8;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

/* Right-Side Hamburger Slide-Over Drawer Styling */
.right-drawer-container {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.97) 0%, rgba(9, 13, 22, 0.99) 100%);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7), 0 0 20px rgba(56, 189, 248, 0.15);
    animation: slideInRight 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(30px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* Glassmorphism Metric Cards */
.metric-card {
    background: linear-gradient(180deg, rgba(22, 31, 48, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px 18px;
    position: relative;
    overflow: hidden;
    transition: all 0.25s ease;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.metric-card:hover {
    border-color: rgba(56, 189, 248, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 8px 26px rgba(0, 0, 0, 0.4);
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
}

.metric-card.critical::before { background: linear-gradient(90deg, #ef4444, #f87171); }
.metric-card.warning::before { background: linear-gradient(90deg, #f97316, #fb923c); }
.metric-card.moderate::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.metric-card.safe::before { background: linear-gradient(90deg, #10b981, #34d399); }
.metric-card.cyan::before { background: linear-gradient(90deg, #06b6d4, #38bdf8); }

.metric-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    color: #f8fafc;
    letter-spacing: -0.02em;
    line-height: 1.1;
}

.metric-subtext {
    font-size: 0.7rem;
    color: #64748b;
    margin-top: 5px;
    font-weight: 500;
}

/* Command Center Panel / Section Cards */
.command-panel {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 18px;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    padding-bottom: 10px;
    margin-bottom: 14px;
}

.panel-title {
    font-size: 0.95rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #f1f5f9;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Risk Badges */
.risk-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.risk-badge.critical {
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.35);
}

.risk-badge.high {
    background: rgba(249, 115, 22, 0.15);
    color: #fb923c;
    border: 1px solid rgba(249, 115, 22, 0.35);
}

.risk-badge.moderate {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.35);
}

.risk-badge.low {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
}

/* Citizen Report Cards */
.citizen-card {
    background: rgba(22, 31, 48, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}

.citizen-card:hover {
    border-color: rgba(56, 189, 248, 0.4);
    background: rgba(30, 41, 59, 0.85);
}

/* Alert Item in Warning Center */
.warning-item {
    background: linear-gradient(90deg, rgba(239, 68, 68, 0.08) 0%, rgba(22, 31, 48, 0.5) 100%);
    border-left: 4px solid #ef4444;
    border-radius: 0 8px 8px 0;
    padding: 12px 14px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Simulation Mode Banner */
.sim-mode-banner {
    background: linear-gradient(90deg, rgba(168, 85, 247, 0.15), rgba(59, 130, 246, 0.15));
    border: 1px solid rgba(168, 85, 247, 0.35);
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #c084fc;
    font-weight: 600;
    font-size: 0.85rem;
}

/* Buttons in Streamlit */
div.stButton > button {
    background: linear-gradient(135deg, #1e293b, #0f172a) !important;
    color: #f1f5f9 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
}

div.stButton > button:hover {
    background: linear-gradient(135deg, #0284c7, #0369a1) !important;
    border-color: #38bdf8 !important;
    color: #ffffff !important;
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.35) !important;
}

div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0284c7, #2563eb) !important;
    border: 1px solid #38bdf8 !important;
    color: #ffffff !important;
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.4) !important;
}

div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #0369a1, #1d4ed8) !important;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.6) !important;
}

/* Sidebar Dark Styling */
section[data-testid="stSidebar"] {
    background-color: #090d16 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
}

/* Radio buttons & Checkboxes */
div[data-testid="stRadio"] label, div[data-testid="stCheckbox"] label {
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: #cbd5e1 !important;
}

/* Inputs */
input, textarea, select {
    background-color: #0f172a !important;
    color: #f8fafc !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 6px !important;
}

/* Streamlit Tabs Customization */
div[data-testid="stTabs"] button {
    background: transparent !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    border: none !important;
    padding: 8px 16px !important;
    border-bottom: 2px solid transparent !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 2px solid #38bdf8 !important;
    background: rgba(56, 189, 248, 0.06) !important;
    border-radius: 6px 6px 0 0 !important;
}
</style>
"""
