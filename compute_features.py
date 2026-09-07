"""
Turns the per-grid daily rainfall log into the 4 engineered features, using
ONLY the reverse-engineered/confirmed rules in config.py:

- rainfall_mm = rainfall_1d_mm = today's daily total (matches Phase 4: these
  two columns were identical in every historical row).
- consecutive_rainy_days: length of the run of consecutive calendar days,
  ending today and including today, where rainfall_mm_day >= RAINY_DAY_THRESHOLD_MM.
  Resets to 0 the moment today doesn't meet the threshold (confirmed from the
  clean 0.997/1.004mm boundary in Phase 4 data — the streak is NOT a trailing
  window that ignores today).
- consecutive_heavy_rain_days: same logic at HEAVY_RAIN_DAY_THRESHOLD_MM.
- Missing calendar day breaks the streak (GAP_POLICY = calendar_day_strict,
  confirmed with you — Phase 4's own gap behavior was undefined, so this is
  the policy going forward, not a guess about the past).
"""
from datetime import timedelta
import pandas as pd

from config import RAINY_DAY_THRESHOLD_MM, HEAVY_RAIN_DAY_THRESHOLD_MM


def compute_streak(daily_log_for_grid: pd.DataFrame, as_of_date, threshold_mm: float) -> int:
    """
    daily_log_for_grid: rows for ONE grid_id, columns date (datetime) and
    rainfall_mm_day, need not be sorted.
    Returns the consecutive-day streak ending at as_of_date, inclusive,
    breaking on any missing calendar day or any day below threshold.
    """
    by_date = daily_log_for_grid.set_index("date")["rainfall_mm_day"]

    streak = 0
    current_day = pd.Timestamp(as_of_date)
    while current_day in by_date.index:
        value = by_date.loc[current_day]
        if pd.isna(value) or value < threshold_mm:
            break
        streak += 1
        current_day = current_day - timedelta(days=1)
    return streak


def compute_grid_features(daily_log_for_grid: pd.DataFrame, as_of_date) -> dict:
    as_of_date = pd.Timestamp(as_of_date)
    by_date = daily_log_for_grid.set_index("date")["rainfall_mm_day"]

    if as_of_date not in by_date.index:
        raise ValueError(
            f"as_of_date {as_of_date.date()} is not present in the daily log for this "
            f"grid — cannot compute features for a day with no fetched rainfall. "
            f"This should have been caught upstream and reported, not silently skipped here."
        )

    today_rainfall = by_date.loc[as_of_date]

    return {
        "rainfall_mm": today_rainfall,
        "rainfall_1d_mm": today_rainfall,
        "consecutive_rainy_days": compute_streak(daily_log_for_grid, as_of_date, RAINY_DAY_THRESHOLD_MM),
        "consecutive_heavy_rain_days": compute_streak(daily_log_for_grid, as_of_date, HEAVY_RAIN_DAY_THRESHOLD_MM),
    }


def compute_all_grid_features(daily_log: pd.DataFrame, as_of_date) -> pd.DataFrame:
    """Returns one row per grid_id that HAS data for as_of_date. Grids missing
    that date are silently excluded here — the orchestrator is responsible for
    diffing against the full grid list and reporting the ones left out."""
    rows = []
    for grid_id, group in daily_log.groupby("grid_id"):
        if pd.Timestamp(as_of_date) not in set(group["date"]):
            continue
        feats = compute_grid_features(group, as_of_date)
        feats["grid_id"] = grid_id
        rows.append(feats)
    return pd.DataFrame(rows)
