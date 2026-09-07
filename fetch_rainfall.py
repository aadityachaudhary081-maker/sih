"""
Fetch step: pulls daily precipitation totals for each grid centroid from
Open-Meteo, in IST calendar days.

Design notes:
- Uses the /v1/forecast endpoint with daily=precipitation_sum and
  timezone=Asia/Kolkata, so Open-Meteo itself buckets each day at local
  midnight instead of us re-bucketing hourly data ourselves.
- past_days=N lets a single call backfill recent history (used to (re)build
  the daily log on first run or after downtime), capped at Open-Meteo's
  92-day limit.
- Today's entry in the response is provisional (the day isn't over yet) —
  it is written to the daily log flagged is_provisional=True and will be
  overwritten by later runs until the day rolls over.
- If Open-Meteo returns no data for a grid (network failure, bad coordinates,
  API outage), this raises/records the failure — it does NOT fabricate a
  value. The caller is responsible for logging it to the missing-data report
  and leaving that grid's locations out of this cycle's output.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional
import requests

from config import OPEN_METEO_FORECAST_URL, OPEN_METEO_MAX_PAST_DAYS, TIMEZONE


@dataclass
class GridFetchResult:
    grid_id: str
    success: bool
    daily_dates: list           # list[date], only present if success
    daily_precip_mm: list       # list[float], parallel to daily_dates
    error: Optional[str] = None


def fetch_grid_daily_rainfall(
    grid_id: str,
    lat: float,
    lon: float,
    past_days: int = 7,
    timeout_s: int = 15,
) -> GridFetchResult:
    """
    Fetch the last `past_days` days of daily rainfall (IST calendar days,
    including today's provisional total) for one grid centroid.
    """
    past_days = min(past_days, OPEN_METEO_MAX_PAST_DAYS)
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "timezone": TIMEZONE,
        "past_days": past_days,
        "forecast_days": 1,  # we only need "today"; don't pull future days into the log
    }

    try:
        resp = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=timeout_s)
        resp.raise_for_status()
        payload = resp.json()
        daily = payload.get("daily", {})
        times = daily.get("time")
        precip = daily.get("precipitation_sum")

        if not times or not precip or len(times) != len(precip):
            return GridFetchResult(
                grid_id=grid_id, success=False, daily_dates=[], daily_precip_mm=[],
                error=f"Malformed/empty response for grid {grid_id} at ({lat},{lon}): {payload}",
            )

        parsed_dates = [date.fromisoformat(t) for t in times]
        # Open-Meteo can return null for a value it hasn't computed yet (e.g.
        # partial current-day data in some edge cases) — treat null as missing,
        # never coerce it to 0.0, since 0.0 is a real, meaningful rainfall value.
        if any(p is None for p in precip):
            missing_dates = [d for d, p in zip(parsed_dates, precip) if p is None]
            return GridFetchResult(
                grid_id=grid_id, success=False, daily_dates=[], daily_precip_mm=[],
                error=f"Grid {grid_id}: API returned null precipitation for {missing_dates}",
            )

        return GridFetchResult(
            grid_id=grid_id, success=True, daily_dates=parsed_dates, daily_precip_mm=precip,
        )

    except (requests.RequestException, ValueError) as e:
        return GridFetchResult(
            grid_id=grid_id, success=False, daily_dates=[], daily_precip_mm=[],
            error=f"Fetch failed for grid {grid_id} at ({lat},{lon}): {e}",
        )


def fetch_all_grids(grid_table, past_days: int = 7) -> list:
    """grid_table: DataFrame with grid_id, centroid_lat, centroid_lon."""
    results = []
    for row in grid_table.itertuples(index=False):
        results.append(
            fetch_grid_daily_rainfall(row.grid_id, row.centroid_lat, row.centroid_lon, past_days=past_days)
        )
    return results
