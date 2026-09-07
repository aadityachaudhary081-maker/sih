# Phase 11 — Confirmed Definitions (not assumptions)

## Reverse-engineered from aizawl_phase4_clean_with_metadata.csv

| Feature | Rule | Evidence |
|---|---|---|
| `rainfall_mm` vs `rainfall_1d_mm` | Identical value — same daily total written to both fields | Equal in 1154/1154 non-null rows |
| Rainy day threshold | `daily_rainfall_mm >= 1.0` | Max value with streak=0 was 0.9971mm; min with streak>=1 was 1.0041mm. No overlap. |
| Heavy rain day threshold | `daily_rainfall_mm >= 25.0` | Max value with streak=0 was 24.62mm; min with streak>=1 was 25.10mm. No overlap. |
| Streak inclusion rule | Streak counts *today*; resets to 0 if today doesn't qualify (not a trailing window ignoring today) | Every below-threshold "today" row had streak=0 regardless of prior days |
| Rainfall granularity | Per grid_id, not per exact lat/lon | Every grid_id/date pair had byte-identical rainfall across all locations in that grid |

## Confirmed with you (policy choices, not reverse-engineered)

Phase 4's behavior across missing-data gaps was **undefined** — it could not be
determined from the historical snapshots, and you confirmed this directly.
These are the choices made for the **live pipeline going forward**:

- **Gap policy:** calendar-day-strict. A missing day resets the streak to 0.
  No bridging across gaps.
- **Timezone:** IST (Asia/Kolkata) — matches Open-Meteo's `timezone` param,
  so "day" boundaries align with local rainy-day reporting.
- **Live data source:** Open-Meteo `/v1/forecast`, no API key required.
- **Schedule:** hourly, since Open-Meteo's current-day total is provisional
  until the day ends — see the scheduling note at the bottom of `pipeline.py`.

## What did NOT change
- Model input feature order/names: `elevation_m, slope_deg, rainfall_mm,
  rainfall_1d_mm, consecutive_rainy_days, consecutive_heavy_rain_days` —
  untouched, still sourced by joining `phase9_terrain_input.csv` (elevation/
  slope, static) with the new `phase9_rainfall_input.csv` (rainfall, now
  live) exactly as Phase 9 already does.
- `phase9_rainfall_input.csv` schema/column order — unchanged, so Phase 10's
  dashboard code needs zero modification.

## Missing-data handling
If Open-Meteo returns nothing (or a null) for a grid's coordinates, that
grid's locations are **excluded from that cycle's output row set** and
logged to `phase11_missing_data_report.csv` with a reason and timestamp.
Nothing is fabricated or silently carried forward as if it were fresh.
