"""
Phase 11 orchestrator — IMD Live Gridded Rainfall Edition.

Run this on a schedule (e.g., daily cron). Each run:
  1. Fetches recent daily rainfall per grid from IMD (India Meteorological Department).
  2. Accounts for IMD's natural 1-day lag by auto-targeting the most recent published date.
  3. Upserts fetched days into the persistent daily log.
  4. Computes rainfall streak features per grid using confirmed thresholds.
  5. Broadcasts grid features to every location_id in that grid.
  6. Writes phase9_rainfall_input.csv with exactly the expected schema.
"""
from datetime import date, datetime
import pandas as pd
from zoneinfo import ZoneInfo

from config import (
    TERRAIN_INPUT_CSV,
    RAINFALL_OUTPUT_CSV,
    DAILY_RAINFALL_LOG_CSV,
    MISSING_DATA_REPORT_CSV,
    TIMEZONE
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
    # Determine fallback today date
    today_date = as_of_date or datetime.now(ZoneInfo(TIMEZONE)).date()

    location_table, grid_table = build_grid_reference(TERRAIN_INPUT_CSV)

    # --- fetch ---
    fetch_results = fetch_all_grids(grid_table, past_days=past_days_to_fetch)

    # DYNAMIC DATE FALLBACK FOR IMD LAG
    # Find the maximum date successfully fetched across all grids.
    # IMD typically lags by 1-2 days.
    all_fetched_dates = []
    for res in fetch_results:
        if res.success and res.daily_dates:
            all_fetched_dates.extend(res.daily_dates)
            
    if all_fetched_dates:
        target_date = max(all_fetched_dates)
        if target_date < today_date:
            print(f"INFO: Auto-adjusted target date to {target_date} (IMD published lag).")
    else:
        target_date = today_date

    daily_log = load_log(DAILY_RAINFALL_LOG_CSV)
    missing_report_rows = []

    for result in fetch_results:
        if not result.success:
            missing_report_rows.append({
                "grid_id": result.grid_id,
                "run_timestamp": datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
                "as_of_date": str(target_date),
                "reason": result.error,
            })
            continue

        provisional_flags = [d == today_date for d in result.daily_dates]
        daily_log = upsert_grid_days(
            daily_log, result.grid_id, result.daily_dates, result.daily_precip_mm, provisional_flags
        )

    save_log(daily_log, DAILY_RAINFALL_LOG_CSV)

    # --- compute features per grid that has data for the dynamically determined target_date ---
    grid_features = compute_all_grid_features(daily_log, target_date)

    fetched_grid_ids = set(grid_features["grid_id"]) if not grid_features.empty else set()
    all_grid_ids = set(grid_table["grid_id"])
    grids_missing_today = all_grid_ids - fetched_grid_ids
    
    for grid_id in grids_missing_today:
        missing_report_rows.append({
            "grid_id": grid_id,
            "run_timestamp": datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
            "as_of_date": str(target_date),
            "reason": f"No rainfall data available for {target_date} after fetch — excluded, not fabricated.",
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
        return target_date

    merged = location_table.merge(grid_features, on="grid_id", how="inner")  # inner: drop missing grids, don't fabricate
    merged["date"] = str(target_date)
    output = merged[OUTPUT_COLUMNS]

    output.to_csv(RAINFALL_OUTPUT_CSV, index=False)
    print(f"Wrote {len(output)} location rows to {RAINFALL_OUTPUT_CSV} "
          f"for date {target_date} ({len(grids_missing_today)} grid(s) excluded).")
    
    # Return the dynamic date so the prediction engine expects the correct one
    return target_date


if __name__ == "__main__":
    run_pipeline()
