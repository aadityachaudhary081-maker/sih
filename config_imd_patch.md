# config.py changes (replace the "--- API ---" block)

```python
# --- API: IMD open gridded real-time rainfall (via imdlib; no key needed) ---
IMD_CACHE_DIR = "data/imd_cache"      # downloaded daily files are stored here
IMD_MAX_LAG_DAYS = 4                  # how far back from yesterday to look for the newest published day
IMD_MAX_PAST_DAYS = 92                # keep same backfill cap as before
IMD_MAX_CELL_DISTANCE_DEG = 0.25      # reject centroids farther than one cell from IMD's grid
IMD_MISSING_SENTINEL = -999.0         # IMD's missing/ocean marker
```

Also fix the bare-filename bug while you're in the file:

```python
TERRAIN_INPUT_CSV = "data/phase9_terrain_input.csv"
RAINFALL_OUTPUT_CSV = "data/phase9_rainfall_input.csv"
DAILY_RAINFALL_LOG_CSV = "data/phase11_grid_rainfall_daily_log.csv"
MISSING_DATA_REPORT_CSV = "data/phase11_missing_data_report.csv"
```

Keep TIMEZONE, thresholds and GAP_POLICY unchanged. Remove OPEN_METEO_* only after
nothing else imports them (grep first).

requirements.txt: add `imdlib`, `xarray`, `numpy`.
