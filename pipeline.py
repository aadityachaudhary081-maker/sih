"""
Phase 11 orchestrator.

Run this on a schedule (see notes at bottom — cadence should match how often
Open-Meteo actually refreshes its model, not an arbitrary interval). Each run:

  1. Loads the 35 grid centroids + 419 location->grid mapping from
     phase9_terrain_input.csv (unchanged from Phase 9 — no schema change).
  2. Fetches recent daily rainfall per grid from Open-Meteo.
  3. Upserts fetched days into the persistent daily log
     (phase11_grid_rainfall_daily_log.csv).
  4. Computes the 4 rainfall features per grid using the confirmed
     thresholds/gap policy.
  5. Broadcasts grid-level features to every location_id in that grid
     (matching how Phase 4's training data was structured).
  6. Writes phase9_rainfall_input.csv with EXACTLY the existing column
     order/schema, so Phase 10's dashboard code needs zero changes.
  7. Any grid the API failed to return data for is excluded from this
     cycle's output and written to phase11_missing_data_report.csv instead
     of being fabricated or silently backfilled with stale data.

WHERE THIS PLUGS IN: this script's write to RAINFALL_OUTPUT_CSV (config.py)
*is* the replacement for Phase 9's static CSV read. Phase 9's own code does
not need to change at all — it already reads phase9_rainfall_input.csv by
that path; this script just becomes what produces that file, on a schedule,
instead of it being a one-time static export. Phase 10 reads the same file
downstream and is untouched.
"""
from datetime import date, datetime
import pandas as pd

from config import (
    TERRAIN_INPUT_CSV,
    RAINFALL_OUTPUT_CSV,
    DAILY_RAINFALL_LOG_CSV,
    MISSING_DATA_REPORT_CSV,
)
from grid_reference import build_grid_reference
from fetch_rainfall import fetch_all_grids
from state_store import load_log, upsert_grid_days, save_log
from compute_features import compute_all_grid_features


OUTPUT_COLUMNS = [
    "location_id", "date", "latitude", "longitude",
    "rainfall_mm", "rainfall_1d_mm",
    "consecutive_rainy_days", "consecutive_heavy_rain_days",
]


def run_pipeline(as_of_date=None, past_days_to_fetch: int = 7):
    as_of_date = as_of_date or date.today()

    location_table, grid_table = build_grid_reference(TERRAIN_INPUT_CSV)

    # --- fetch ---
    fetch_results = fetch_all_grids(grid_table, past_days=past_days_to_fetch)

    daily_log = load_log(DAILY_RAINFALL_LOG_CSV)
    missing_report_rows = []

    for result in fetch_results:
        if not result.success:
            missing_report_rows.append({
                "grid_id": result.grid_id,
                "run_timestamp": datetime.now().isoformat(),
                "as_of_date": str(as_of_date),
                "reason": result.error,
            })
            continue

        # Everything except the last day is final; the last day (today, if
        # as_of_date is in the returned range) is still in progress.
        provisional_flags = [d == date.today() for d in result.daily_dates]
        daily_log = upsert_grid_days(
            daily_log, result.grid_id, result.daily_dates, result.daily_precip_mm, provisional_flags
        )

    save_log(daily_log, DAILY_RAINFALL_LOG_CSV)

    # --- compute features per grid that has data for as_of_date ---
    grid_features = compute_all_grid_features(daily_log, as_of_date)

    fetched_grid_ids = set(grid_features["grid_id"]) if not grid_features.empty else set()
    all_grid_ids = set(grid_table["grid_id"])
    grids_missing_today = all_grid_ids - fetched_grid_ids
    for grid_id in grids_missing_today:
        missing_report_rows.append({
            "grid_id": grid_id,
            "run_timestamp": datetime.now().isoformat(),
            "as_of_date": str(as_of_date),
            "reason": f"No rainfall data available for {as_of_date} after fetch — excluded, not fabricated.",
        })

    if missing_report_rows:
        pd.DataFrame(missing_report_rows).to_csv(MISSING_DATA_REPORT_CSV, index=False)
        affected_locations = location_table[location_table["grid_id"].isin(grids_missing_today)]
        print(
            f"WARNING: {len(grids_missing_today)} grid(s) / "
            f"{len(affected_locations)} location(s) have NO rainfall row this cycle. "
            f"See {MISSING_DATA_REPORT_CSV}."
        )

    # --- broadcast grid features to every location in that grid ---
    if grid_features.empty:
        print("ERROR: no grids returned usable data this cycle — output NOT written.")
        return

    merged = location_table.merge(grid_features, on="grid_id", how="inner")  # inner: drop missing grids, don't fabricate
    merged["date"] = str(as_of_date)
    output = merged[OUTPUT_COLUMNS]

    output.to_csv(RAINFALL_OUTPUT_CSV, index=False)
    print(f"Wrote {len(output)} location rows to {RAINFALL_OUTPUT_CSV} "
          f"({len(grids_missing_today)} grid(s) excluded this cycle).")


if __name__ == "__main__":
    run_pipeline()

# --- Scheduling note ---
# Open-Meteo's underlying model runs update multiple times a day, but the
# CURRENT day's precipitation_sum is inherently provisional until the day
# ends (it's a running total of hours observed so far). Recommended cadence:
# run hourly via cron/systemd timer. Each hourly run:
#   - refines today's provisional total (rewrites that one row)
#   - finalizes yesterday once the API stops revising it
#   - naturally self-heals from a single missed run, since past_days=7
#     re-fetches a week of history every time, not just "since last run"
# Example cron line (adjust path/venv):
#   0 * * * *  cd /path/to/phase11 && /usr/bin/python3 pipeline.py >> phase11.log 2>&1
