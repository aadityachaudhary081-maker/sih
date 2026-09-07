"""
Phase 9/11 Prediction Generator
================================
The script that was missing from the repo: this is what actually produces
the three files app.py (Phase 10) reads. Nothing here touches app.py's
logic — it only needs to keep writing files in the exact schema app.py
already validates against.

Pipeline:
  phase9_terrain_input.csv (static)  ---\
                                          +--> join on location_id --> 6 features --> model.predict_proba --> risk fields
  Phase 11 live rainfall (pipeline.py) --/

Run this on the same schedule as pipeline.py (see pipeline.py's scheduling
note) — right after it, since this script consumes pipeline.py's output.
"""
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

import pipeline as phase11_pipeline  # Phase 11 rainfall fetch + feature computation
from config import TERRAIN_INPUT_CSV, RAINFALL_OUTPUT_CSV

warnings.filterwarnings("ignore", category=UserWarning)  # sklearn version-mismatch warning; see requirements.txt note

MODEL_ARTIFACT_PATH = "landslide_random_forest_production_artifact.joblib"

DATA_DIR = Path("data")
LATEST_RISK_PATH = DATA_DIR / "latest_location_risk.csv"
ALL_PREDICTIONS_PATH = DATA_DIR / "all_daily_live_predictions.csv"
RISK_SUMMARY_PATH = DATA_DIR / "risk_summary.json"

# Dashboard-presentation-only bands (NOT the production WARNING/NO_WARNING
# decision, which uses the artifact's own operating_threshold). HIGH starts
# exactly at the operating threshold so "HIGH/CRITICAL" never contradicts
# "WARNING" on the dashboard.
RISK_BANDS = [
    (0.25, "LOW"),
    (0.47, "MODERATE"),
    (0.75, "HIGH"),
    (float("inf"), "CRITICAL"),
]

REQUIRED_COLUMNS = [
    "location_id", "date", "latitude", "longitude",
    "elevation_m", "slope_deg",
    "rainfall_mm", "rainfall_1d_mm",
    "consecutive_rainy_days", "consecutive_heavy_rain_days",
    "landslide_probability", "probability_percent",
    "operating_threshold", "model_decision", "warning_status",
    "risk_level", "prediction_timestamp_utc",
]


def assign_risk_level(probability: float) -> str:
    for upper_bound, label in RISK_BANDS:
        if probability < upper_bound:
            return label
    return RISK_BANDS[-1][1]


def load_artifact(path: str) -> dict:
    art = joblib.load(path)
    required_keys = {"model", "features", "operating_threshold"}
    missing = required_keys - art.keys()
    if missing:
        raise ValueError(f"Model artifact is missing expected key(s): {missing}")
    return art


def build_feature_frame(terrain_csv: str, rainfall_csv: str, feature_order: list) -> pd.DataFrame:
    terrain = pd.read_csv(terrain_csv)
    rainfall = pd.read_csv(rainfall_csv)

    merged = rainfall.merge(
        terrain[["location_id", "latitude", "longitude", "elevation_m", "slope_deg"]],
        on="location_id",
        how="inner",  # a location missing from rainfall (API failure) is dropped, not fabricated
        suffixes=("", "_terrain"),
    )
    missing_locations = set(terrain["location_id"]) - set(merged["location_id"])
    if missing_locations:
        print(f"NOTE: {len(missing_locations)} location(s) excluded from this run "
              f"(no rainfall row — see phase11_missing_data_report.csv): "
              f"{sorted(missing_locations)[:5]}...")

    for col in feature_order:
        if col not in merged.columns:
            raise ValueError(f"Required model feature '{col}' not present after merge.")
    return merged


def run_predictions(as_of_date=None):
    as_of_date = as_of_date or datetime.now(timezone.utc).date().isoformat()

    # Step 1: refresh live rainfall (Phase 11) — writes RAINFALL_OUTPUT_CSV
    phase11_pipeline.run_pipeline(as_of_date=as_of_date)

    # Freshness check: if the fetch failed for ALL grids, run_pipeline leaves
    # RAINFALL_OUTPUT_CSV untouched — it will still be sitting there from a
    # previous run, OR (worse) from the original static/historical export,
    # which has a DIFFERENT date per location/row (each location's own
    # historical event date), not a single uniform "today". A genuine live
    # run always broadcasts ONE date across every row (see pipeline.py).
    # So the correct freshness test isn't "does as_of_date appear somewhere"
    # (a stale historical file can coincidentally contain any date) — it's
    # "is the ENTIRE file uniformly dated as_of_date".
    rainfall_dates = set(pd.read_csv(RAINFALL_OUTPUT_CSV)["date"].astype(str).unique())
    if rainfall_dates != {str(as_of_date)}:
        raise RuntimeError(
            f"{RAINFALL_OUTPUT_CSV} is not uniformly dated {as_of_date} "
            f"(found date(s): {sorted(rainfall_dates)[:5]}{'...' if len(rainfall_dates) > 5 else ''}). "
            f"This means the live fetch failed for this cycle and the file still "
            f"holds stale/historical data — see phase11_missing_data_report.csv. "
            f"Refusing to publish predictions built on stale rainfall data. "
            f"Fix the fetch (check network/API status) and re-run."
        )

    # Step 2: load model + join terrain
    art = load_artifact(MODEL_ARTIFACT_PATH)
    model = art["model"]
    feature_order = art["features"]
    operating_threshold = art["operating_threshold"]
    model_name = art.get("selected_model", "Random Forest")

    merged = build_feature_frame(TERRAIN_INPUT_CSV, RAINFALL_OUTPUT_CSV, feature_order)

    # Step 3: predict — feature order MUST match the artifact's own list,
    # never re-derived or assumed from column order in the CSV.
    X = merged[feature_order]
    probabilities = model.predict_proba(X)[:, 1]

    prediction_timestamp = datetime.now(timezone.utc).isoformat()

    result = merged[["location_id", "latitude", "longitude", "elevation_m", "slope_deg",
                      "rainfall_mm", "rainfall_1d_mm",
                      "consecutive_rainy_days", "consecutive_heavy_rain_days"]].copy()
    result["date"] = str(as_of_date)  # single source of truth, not trusted from the merged file
    result["landslide_probability"] = probabilities
    result["probability_percent"] = probabilities * 100
    result["operating_threshold"] = operating_threshold
    result["model_decision"] = (probabilities >= operating_threshold).astype(int)
    result["warning_status"] = result["model_decision"].map({1: "WARNING", 0: "NO_WARNING"})
    result["risk_level"] = result["landslide_probability"].apply(assign_risk_level)
    result["prediction_timestamp_utc"] = prediction_timestamp
    result = result[REQUIRED_COLUMNS]

    # Step 4: write latest_location_risk.csv (one row per location, this run's values)
    DATA_DIR.mkdir(exist_ok=True)
    result.to_csv(LATEST_RISK_PATH, index=False)

    # Step 5: append to all_daily_live_predictions.csv, upserting on
    # (location_id, date) so re-running the same day overwrites rather than
    # duplicates.
    if ALL_PREDICTIONS_PATH.exists():
        history = pd.read_csv(ALL_PREDICTIONS_PATH)
        history = history[~(
            history["location_id"].isin(result["location_id"]) & (history["date"] == result["date"].iloc[0])
        )]
        history = pd.concat([history, result], ignore_index=True)
    else:
        history = result
    history.to_csv(ALL_PREDICTIONS_PATH, index=False)

    # Step 6: risk_summary.json
    summary = {
        "model_name": model_name,
        "operating_threshold": float(operating_threshold),
        "total_locations": int(result["location_id"].nunique()),
        "total_prediction_records": int(len(history)),
        "warnings": int((result["warning_status"] == "WARNING").sum()),
        "no_warnings": int((result["warning_status"] == "NO_WARNING").sum()),
        "mean_landslide_probability": float(result["landslide_probability"].mean()),
        "prediction_timestamp_utc": prediction_timestamp,
        "phase": 9,
    }
    with open(RISK_SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote {len(result)} location predictions "
          f"({summary['warnings']} WARNING, {summary['no_warnings']} NO_WARNING).")


if __name__ == "__main__":
    run_predictions()
