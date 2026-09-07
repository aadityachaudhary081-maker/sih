"""
Phase 11 configuration — real-time rainfall integration.

Every threshold below was reverse-engineered from aizawl_phase4_clean_with_metadata.csv
by finding the exact boundary where consecutive_rainy_days / consecutive_heavy_rain_days
flips between 0 and nonzero. None of these are assumed defaults — see the confirmation
report (phase11_definition_confirmation.md) for the evidence.
"""

# --- Reverse-engineered from Phase 4 data (see confirmation report) ---

# "Rainy day" boundary: max value with streak==0 was 0.9971mm,
# min value with streak>=1 was 1.0041mm. Zero overlap in 1154 rows.
RAINY_DAY_THRESHOLD_MM = 1.0

# "Heavy rain day" boundary: max value with streak==0 was 24.62mm,
# min value with streak>=1 was 25.10mm. Zero overlap in 1154 rows.
HEAVY_RAIN_DAY_THRESHOLD_MM = 25.0

# rainfall_mm and rainfall_1d_mm were identical in every non-null historical row.
# Both output fields are populated from the same single daily total.

# Streak semantics confirmed from data: the streak counts *today* and requires
# *today* to meet the threshold, or it resets to 0 immediately (not "any day
# in a trailing window" — genuinely a "consecutive ending today" streak).

# --- Policy decisions confirmed with you (not reverse-engineered — Phase 4's
#     gap behavior was undefined, so these are your explicit choices for the
#     live pipeline going forward) ---

# Missing calendar day => streak resets to 0. No bridging across gaps.
GAP_POLICY = "calendar_day_strict"

# "Day" boundaries are defined in IST, matching Open-Meteo's timezone param.
TIMEZONE = "Asia/Kolkata"

# --- API ---
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_MAX_PAST_DAYS = 92  # hard API limit; used for initial backfill only

# --- File locations (adjust to your actual production paths) ---
TERRAIN_INPUT_CSV = "phase9_terrain_input.csv"
RAINFALL_OUTPUT_CSV = "phase9_rainfall_input.csv"          # Phase 10 reads this — schema unchanged
DAILY_RAINFALL_LOG_CSV = "phase11_grid_rainfall_daily_log.csv"  # new: per-grid persistent state
MISSING_DATA_REPORT_CSV = "phase11_missing_data_report.csv"     # new: what the API failed to return
