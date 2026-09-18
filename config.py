import os

# Threshold boundaries
RAINY_DAY_THRESHOLD_MM = 1.0
HEAVY_RAIN_DAY_THRESHOLD_MM = 25.0
GAP_POLICY = "calendar_day_strict"
TIMEZONE = "Asia/Kolkata"

# IMD Gridded Rainfall Configuration
IMD_CACHE_DIR = os.path.join("data", "imd_cache")
IMD_MAX_LAG_DAYS = 30
IMD_MAX_PAST_DAYS = 90
IMD_VARIABLE = "rain"
IMD_MAX_CELL_DISTANCE_DEG = 0.25
IMD_MISSING_SENTINEL = -999.0

# Open-Meteo Legacy Compatibility (if referenced anywhere)
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_MAX_PAST_DAYS = 92

# Production Data Paths
DATA_DIR = "data"
TERRAIN_INPUT_CSV = os.path.join(DATA_DIR, "phase9_terrain_input.csv")
RAINFALL_OUTPUT_CSV = os.path.join(DATA_DIR, "phase9_rainfall_input.csv")
DAILY_RAINFALL_LOG_CSV = os.path.join(DATA_DIR, "phase11_grid_rainfall_daily_log.csv")
MISSING_DATA_REPORT_CSV = os.path.join(DATA_DIR, "phase11_missing_data_report.csv")
DAILY_RAINFALL_LOG_CSV = os.path.join(DATA_DIR, "phase11_grid_rainfall_daily_log.csv")
MISSING_DATA_REPORT_CSV = os.path.join(DATA_DIR, "phase11_missing_data_report.csv")


