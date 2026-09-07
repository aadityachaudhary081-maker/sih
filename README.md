# SIH Landslide Early Warning System — Phase 10

Phase 10 Interactive Dashboard — Powered by Phase 9 Prediction Outputs

## Folder Structure

```
SIH_Landslide_Dashboard/
│
├── app.py
├── requirements.txt
├── README.md
│
└── data/
    ├── latest_location_risk.csv
    ├── all_daily_live_predictions.csv
    └── risk_summary.json
```

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Input Data

This dashboard is a **visualization and monitoring layer** over the Phase 9
prediction pipeline output. It does not train, retrain, or re-run the
underlying Random Forest model — it only reads and displays the following
three files, which must be present in the `data/` folder:

- **`latest_location_risk.csv`** — the most recent prediction for each
  monitored location (418 locations). Used for the risk map, warning
  center, location explorer, and current-state analytics.
- **`all_daily_live_predictions.csv`** — the full historical record of
  daily predictions (1154 rows). Used for historical probability trends
  and location-wise history.
- **`risk_summary.json`** — Phase 9 summary metadata (totals, risk-level
  counts, operating threshold, model name). Used for dashboard KPI values
  and system information, with a CSV-based fallback if any field is
  missing.

## Important Note

The dashboard:

- does **not** retrain the model
- does **not** modify model predictions or probabilities
- does **not** regenerate rainfall features
- does **not** fabricate or simulate data
- reads the operating threshold **dynamically** from `risk_summary.json`
  (falling back to the CSV data if needed) — it is never hardcoded
- keeps the production **WARNING / NO_WARNING** decision strictly separate
  from the dashboard's own **LOW / MODERATE / HIGH / CRITICAL** presentation
  categories; the latter never overrides or is implied to be the same as
  the former
