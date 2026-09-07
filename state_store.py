"""
Maintains phase11_grid_rainfall_daily_log.csv — the persistent per-grid daily
rainfall history that consecutive_rainy_days / consecutive_heavy_rain_days are
computed from.

This is what makes the gap policy (calendar_day_strict) meaningful: if a day
is genuinely absent from this log (API was down, grid excluded that cycle),
the feature computation step will see the gap and reset the streak — it does
not need separate gap-tracking logic, the log's structure IS the gap record.

Columns: grid_id, date (ISO string), rainfall_mm_day, is_provisional
"""
import pandas as pd
from pathlib import Path


LOG_COLUMNS = ["grid_id", "date", "rainfall_mm_day", "is_provisional"]


def load_log(path: str) -> pd.DataFrame:
    if Path(path).exists():
        df = pd.read_csv(path, parse_dates=["date"])
        return df
    return pd.DataFrame(columns=LOG_COLUMNS)


def upsert_grid_days(log: pd.DataFrame, grid_id: str, dates, rainfall_values, provisional_flags) -> pd.DataFrame:
    """
    Upsert (grid_id, date) rows. A row for the same grid_id+date that already
    exists is overwritten (this is how a provisional "today" gets finalized
    and how yesterday's provisional value gets corrected if the API revises
    it). Never used to invent a date that wasn't actually fetched.
    """
    new_rows = pd.DataFrame({
        "grid_id": grid_id,
        "date": pd.to_datetime(dates),
        "rainfall_mm_day": rainfall_values,
        "is_provisional": provisional_flags,
    })
    if log.empty:
        return new_rows

    key_cols = ["grid_id", "date"]
    log = log.set_index(key_cols)
    new_rows_idx = new_rows.set_index(key_cols)
    log = new_rows_idx.combine_first(log)  # new_rows values win on overlap
    log.update(new_rows_idx)
    return log.reset_index()


def save_log(log: pd.DataFrame, path: str) -> None:
    log = log.sort_values(["grid_id", "date"])
    log.to_csv(path, index=False)
