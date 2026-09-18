"""
Fetch step: pulls daily precipitation totals for each grid centroid from the
India Meteorological Department (IMD) open gridded real-time rainfall product
(0.25 deg x 0.25 deg, daily, mm/day) via the `imdlib` package.

No subscription, API key or registration is required.

Design notes (what changed vs. the Open-Meteo version):
- Interface is unchanged: GridFetchResult / fetch_grid_daily_rainfall /
  fetch_all_grids keep the same signatures, so pipeline.py needs no edits.
- IMD publishes one file per day for the whole country. We download the whole
  window ONCE, then sample the nearest 0.25 deg cell for every centroid.
- IMD's real-time product lags: today's (in-progress) IST day is never
  available. The window therefore ends at the newest day IMD has actually
  published (searched backwards from yesterday, up to IMD_MAX_LAG_DAYS).
  There is no provisional "today" row any more.
- Missing data is never turned into 0.0. IMD marks missing/ocean cells with
  -999; a grid whose cell is missing on any requested day is returned as a
  failure so the caller logs it in the missing-data report, exactly like the
  Open-Meteo version treated nulls.
- Values are IMD's 08:30 IST-to-08:30 IST rainfall day, not midnight-to-
  midnight. It is still one value per IST calendar date, so the calendar-day
  gap policy in config.py is unchanged.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
import math

from config import (
    IMD_CACHE_DIR,
    IMD_MAX_LAG_DAYS,
    IMD_MAX_PAST_DAYS,
    IMD_MAX_CELL_DISTANCE_DEG,
    IMD_MISSING_SENTINEL,
)


@dataclass
class GridFetchResult:
    grid_id: str
    success: bool
    daily_dates: list      # list[date], only present if success
    daily_precip_mm: list  # list[float], parallel to daily_dates
    error: Optional[str] = None


_WINDOW_CACHE: dict = {}


def _load_window(start: date, end: date):
    """Download (if needed) and open IMD real-time rain for [start, end]. Returns xarray Dataset."""
    key = (start, end)
    if key in _WINDOW_CACHE:
        return _WINDOW_CACHE[key]
    import os
    import imdlib as imd  # imported lazily so config/tests don't need it installed

    os.makedirs(IMD_CACHE_DIR, exist_ok=True)
    s, e = start.isoformat(), end.isoformat()
    imd.get_real_data("rain", s, e, IMD_CACHE_DIR)
    ds = imd.open_real_data("rain", s, e, IMD_CACHE_DIR).get_xarray()
    _WINDOW_CACHE[key] = ds
    return ds


def _newest_available_end(today: date):
    """Walk back from yesterday until IMD has a file. Returns (end_date, dataset) or (None, None)."""
    last_err = None
    for lag in range(1, IMD_MAX_LAG_DAYS + 1):
        end = today - timedelta(days=lag)
        try:
            ds = _load_window(end, end)
            if ds is not None and _has_any_valid(ds):
                return end, last_err
        except Exception as exc:  # network/file errors for a not-yet-published day
            last_err = exc
    return None, last_err


def _has_any_valid(ds) -> bool:
    import numpy as np
    vals = ds["rain"].values
    return bool(np.isfinite(vals).any() and (vals > IMD_MISSING_SENTINEL / 2).any())


def _sample_cell(ds, lat: float, lon: float):
    """Nearest-cell daily series at (lat, lon). Returns (dates, values, err)."""
    import numpy as np

    lat_c = float(ds["lat"].sel(lat=lat, method="nearest"))
    lon_c = float(ds["lon"].sel(lon=lon, method="nearest"))
    if abs(lat_c - lat) > IMD_MAX_CELL_DISTANCE_DEG or abs(lon_c - lon) > IMD_MAX_CELL_DISTANCE_DEG:
        return None, None, f"({lat},{lon}) is outside IMD grid coverage (nearest cell {lat_c},{lon_c})"
    series = ds["rain"].sel(lat=lat_c, lon=lon_c)
    times = [np.datetime64(t, "D").astype(object) for t in series["time"].values]
    values = [float(v) for v in series.values]
    return times, values, None


def fetch_grid_daily_rainfall(
    grid_id: str,
    lat: float,
    lon: float,
    past_days: int = 7,
    timeout_s: int = 15,  # kept for signature compatibility; imdlib manages its own I/O
) -> GridFetchResult:
    """Last `past_days` IST days of IMD rainfall for one centroid, ending at the newest published day."""
    return _fetch_many([(grid_id, lat, lon)], past_days)[0]


def _fetch_many(rows, past_days: int) -> list:
    past_days = max(1, min(past_days, IMD_MAX_PAST_DAYS))
    fail = lambda gid, msg: GridFetchResult(gid, False, [], [], error=msg)
    try:
        end, err = _newest_available_end(date.today())
        if end is None:
            return [fail(r[0], f"IMD real-time rainfall not available for the last "
                               f"{IMD_MAX_LAG_DAYS} days: {err}") for r in rows]
        start = end - timedelta(days=past_days - 1)
        ds = _load_window(start, end)
    except Exception as exc:
        return [fail(r[0], f"IMD download failed: {exc}") for r in rows]

    expected = [start + timedelta(days=i) for i in range(past_days)]
    out = []
    for gid, lat, lon in rows:
        try:
            dates, vals, err = _sample_cell(ds, lat, lon)
            if err:
                out.append(fail(gid, f"Grid {gid}: {err}"))
                continue
            by_date = dict(zip(dates, vals))
            missing = [d for d in expected
                       if d not in by_date or not math.isfinite(by_date[d])
                       or by_date[d] <= IMD_MISSING_SENTINEL / 2]
            if missing:
                out.append(fail(gid, f"Grid {gid}: IMD has no valid rainfall for {missing}"))
                continue
            out.append(GridFetchResult(gid, True, expected, [max(0.0, by_date[d]) for d in expected]))
        except Exception as exc:
            out.append(fail(gid, f"Fetch failed for grid {gid} at ({lat},{lon}): {exc}"))
    return out


def fetch_all_grids(grid_table, past_days: int = 7) -> list:
    """grid_table: DataFrame with grid_id, centroid_lat, centroid_lon."""
    rows = [(r.grid_id, r.centroid_lat, r.centroid_lon) for r in grid_table.itertuples(index=False)]
    return _fetch_many(rows, past_days)
