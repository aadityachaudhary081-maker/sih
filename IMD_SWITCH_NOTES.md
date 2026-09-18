# Open-Meteo references found during the NEXORA port

These are places where "Open-Meteo" appears as **display text** in the ported
UI. They were copied verbatim so the port stays faithful to the source repo.
Each one needs to change when the rainfall source switches to IMD.

None of these are functional API calls — they are strings shown to the user.
The actual API call lives in `fetch_rainfall.py` / `config.py`
(`OPEN_METEO_FORECAST_URL`), which is a separate change.

| File | Location | Current text |
|---|---|---|
| `components/overview.py` | Rainfall Telemetry card footer | "Strict calendar-day gap policy. Synced hourly via Open-Meteo Aizawl centroids." |
| `components/rainfall_view.py` | Panel header subtitle | "OPEN-METEO IST REAL-TIME SENSING • CALENDAR-DAY STRICT LOG" |
| `components/system_health.py` | Subsystem Diagnostics row | "🌧️ Open-Meteo IST Ingestion Pipeline" |
| `components/system_health.py` | End-to-end flow diagram, first line | "Open-Meteo Forecast API (IST Timezone)" |

## Other inconsistencies noticed in the source repo (not introduced by the port)

- **Station count mismatch.** `components/overview.py` KPI card subtext says
  "35 Grid Centroids in Aizawl", while `components/sidebar.py`,
  `components/risk_map.py`, `components/rainfall_view.py` and
  `components/whatif_simulation.py` all say 419. Decide which is correct
  before demoing.

- **`config.py` path bug.** The source repo still has
  `TERRAIN_INPUT_CSV = "phase9_terrain_input.csv"` with no `data/` prefix —
  the same bug already fixed in your repo. Don't copy this file over blindly.

## Still to port

- `app.py` (the main router that wires all 12 components together)
- `styles.py` (the Command Center CSS design system)
