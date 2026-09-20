"""
Phase 9/11 Prediction Generator — IMD Lag-Aware Edition
================================
Consumes the dynamically dated RAINFALL_OUTPUT_CSV produced by pipeline.py.
Merges with static terrain features and passes through the Random Forest artifact.
"""
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from zoneinfo import ZoneInfo

import pipeline as phase11_pipeline  # Phase 11 rainfall fetch + feature computation
from config import TERRAIN_INPUT_CSV, RAINFALL_OUTPUT_CSV, TIMEZONE

warnings.filterwarnings("ignore", category=UserWarning)

MODEL_ARTIFACT_PATH = "landslide_random_forest_production_artifact.joblib"

DATA_DIR = Path("data")
LATEST_RISK_PATH = DATA_DIR / "latest_location_risk.csv"
ALL_PREDICTIONS_PATH = DATA_DIR / "all_daily_live_predictions.csv"
RISK_SUMMARY_PATH = DATA_DIR / "risk_summary.json"

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
        how="inner",
        suffixes=("", "_terrain"),
    )
    missing_locations = set(terrain["location_id"]) - set(merged["location_id"])
    if missing_locations:
        print(f"NOTE: {len(missing_locations)} location(s) excluded from this run.")

    for col in feature_order:
        if col not in merged.columns:
            raise ValueError(f"Required model feature '{col}' not present after merge.")
    return merged


def run_predictions(as_of_date=None):
    # Execute pipeline. It returns the dynamic IMD-lag-adjusted date.
    resolved_date = phase11_pipeline.run_pipeline(as_of_date=as_of_date)
    
    if not resolved_date:
        raise RuntimeError("Pipeline failed to return a valid resolved target date.")

    # Freshness check: Validates the file contains strictly the dynamically resolved date
    rainfall_df = pd.read_csv(RAINFALL_OUTPUT_CSV)
    rainfall_dates = set(rainfall_df["date"].astype(str).unique())
    
    if rainfall_dates != {str(resolved_date)}:
        raise RuntimeError(
            f"{RAINFALL_OUTPUT_CSV} is not uniformly dated {resolved_date} "
            f"(found: {sorted(rainfall_dates)[:3]}...). Fetch failure or stale data."
        )

    # Load artifact and prep features
    art = load_artifact(MODEL_ARTIFACT_PATH)
    model = art["model"]
    feature_order = art["features"]
    operating_threshold = art["operating_threshold"]
    model_name = art.get("selected_model", "Random Forest")

    merged = build_feature_frame(TERRAIN_INPUT_CSV, RAINFALL_OUTPUT_CSV, feature_order)

    # Predict
    X = merged[feature_order]
    probabilities = model.predict_proba(X)[:, 1]

    prediction_timestamp = datetime.now(timezone.utc).isoformat()

    result = merged[["location_id", "latitude", "longitude", "elevation_m", "slope_deg",
                      "rainfall_mm", "rainfall_1d_mm",
                      "consecutive_rainy_days", "consecutive_heavy_rain_days"]].copy()
                      
    result["date"] = str(resolved_date)
    result["landslide_probability"] = probabilities
    result["probability_percent"] = probabilities * 100
    result["operating_threshold"] = operating_threshold
    result["model_decision"] = (probabilities >= operating_threshold).astype(int)
    result["warning_status"] = result["model_decision"].map({1: "WARNING", 0: "NO_WARNING"})
    result["risk_level"] = result["landslide_probability"].apply(assign_risk_level)
    result["prediction_timestamp_utc"] = prediction_timestamp
    result = result[REQUIRED_COLUMNS]

    # Write output
    DATA_DIR.mkdir(exist_ok=True)
    result.to_csv(LATEST_RISK_PATH, index=False)

    # Upsert history
    if ALL_PREDICTIONS_PATH.exists():
        history = pd.read_csv(ALL_PREDICTIONS_PATH)
        history = history[~(
            history["location_id"].isin(result["location_id"]) & (history["date"] == result["date"].iloc[0])
        )]
        history = pd.concat([history, result], ignore_index=True)
    else:
        history = result
    history.to_csv(ALL_PREDICTIONS_PATH, index=False)

    # Summary
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

    print(f"Wrote {len(result)} predictions for IMD lagged date {resolved_date} "
          f"({summary['warnings']} WARNING, {summary['no_warnings']} NO_WARNING).")


if __name__ == "__main__":
    from datetime import date, timedelta
    
    print("--- MASS BACKFILL: JAN 1 to SEPT 19 ---")
    start_date = date(2026, 1, 1)
    end_date = date(2026, 9, 19)
    
    current_date = start_date
    while current_date <= end_date:
        print(f"Processing: {current_date}")
        try:
            # Generate pipeline features and predictions for this specific date
            run_predictions(as_of_date=current_date)
        except Exception as e:
            print(f"Skipped {current_date}: {e}")
            
        current_date += timedelta(days=1)
        
    print("--- BACKFILL COMPLETE. RUNNING STANDARD CYCLE ---")
    run_predictions()
