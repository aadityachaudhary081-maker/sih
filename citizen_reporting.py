"""
NEXORA Citizen Reporting System
- Geo-tagged ground hazard reporting
- HTML5 Browser Geolocation capture (± accuracy, timestamp)
- Image storage and metadata persistence in data/citizen_reports.json
- Spatial AI Risk Correlation: Haversine distance matching against Aizawl 419 monitoring stations
"""

import json
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import pandas as pd
from PIL import Image

DATA_DIR = Path("data")
CITIZEN_REPORTS_FILE = DATA_DIR / "citizen_reports.json"
CITIZEN_UPLOADS_DIR = DATA_DIR / "citizen_uploads"

# Allowed hazard observation types
HAZARD_TYPES = [
    "Landslide",
    "Soil movement",
    "Road crack",
    "Rockfall",
    "Waterlogging",
    "Drainage blockage",
    "Slope failure",
    "Other",
]

# Verification statuses
STATUS_PENDING = "Pending Verification"
STATUS_VERIFIED = "Verified Ground Hazard"
STATUS_RESOLVED = "Resolved"
STATUS_OPTIONS = [STATUS_PENDING, STATUS_VERIFIED, STATUS_RESOLVED]


def init_storage():
    """Ensure data directories and report files exist with initial sample data."""
    DATA_DIR.mkdir(exist_ok=True)
    CITIZEN_UPLOADS_DIR.mkdir(exist_ok=True)

    if not CITIZEN_REPORTS_FILE.exists():
        # Seed realistic initial reports for Aizawl District for immediate demo readiness
        seed_reports = [
            {
                "id": "REP-2026-AIZ-001",
                "image_path": "data/citizen_uploads/seed_crack_chaltlang.jpg",
                "latitude": 23.7428,
                "longitude": 92.7185,
                "gps_accuracy_m": 6.5,
                "timestamp": "2026-09-10T14:22:00+05:30",
                "report_type": "Road crack",
                "description": "Deep transverse tensile cracks developing across Chaltlang Road after heavy continuous downpour.",
                "status": STATUS_VERIFIED,
                "nearest_zone_id": "AIZ_GRID_040_23.738575_92.694194",
                "distance_to_zone_m": 480.0,
                "zone_risk_level": "HIGH",
                "zone_probability": 0.507,
            },
            {
                "id": "REP-2026-AIZ-002",
                "image_path": "data/citizen_uploads/seed_debris_bawngkawn.jpg",
                "latitude": 23.7512,
                "longitude": 92.7304,
                "gps_accuracy_m": 8.0,
                "timestamp": "2026-09-10T16:45:00+05:30",
                "report_type": "Soil movement",
                "description": "Retaining wall deformation and minor mud displacement on slope above residential houses in Bawngkawn.",
                "status": STATUS_PENDING,
                "nearest_zone_id": "AIZ_GRID_040_23.738889_92.696389",
                "distance_to_zone_m": 1250.0,
                "zone_risk_level": "HIGH",
                "zone_probability": 0.528,
            },
            {
                "id": "REP-2026-AIZ-003",
                "image_path": "data/citizen_uploads/seed_rockfall_durtlang.jpg",
                "latitude": 23.7745,
                "longitude": 92.7390,
                "gps_accuracy_m": 5.2,
                "timestamp": "2026-09-10T18:10:00+05:30",
                "report_type": "Rockfall",
                "description": "Boulders and loose scree dislodged onto Durtlang main ridge road, partially obstructing one lane.",
                "status": STATUS_VERIFIED,
                "nearest_zone_id": "AIZ_GRID_040_23.740278_92.697222",
                "distance_to_zone_m": 3100.0,
                "zone_risk_level": "CRITICAL",
                "zone_probability": 0.785,
            },
        ]
        with open(CITIZEN_REPORTS_FILE, "w") as f:
            json.dump(seed_reports, f, indent=2)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in meters using Haversine formula."""
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def find_nearest_monitoring_zone(
    lat: float, lon: float, latest_risk_df: Optional[pd.DataFrame] = None
) -> Tuple[Optional[str], float, Optional[str], float]:
    """
    Finds the nearest AI monitored station in Aizawl dataset.
    Returns: (location_id, distance_m, risk_level, probability)
    """
    if latest_risk_df is None or latest_risk_df.empty:
        risk_path = DATA_DIR / "latest_location_risk.csv"
        if risk_path.exists():
            latest_risk_df = pd.read_csv(risk_path)
        else:
            return None, 0.0, None, 0.0

    if "latitude" not in latest_risk_df.columns or "longitude" not in latest_risk_df.columns:
        return None, 0.0, None, 0.0

    min_dist = float("inf")
    nearest_row = None

    for _, row in latest_risk_df.iterrows():
        dist = haversine_distance(lat, lon, float(row["latitude"]), float(row["longitude"]))
        if dist < min_dist:
            min_dist = dist
            nearest_row = row

    if nearest_row is not None:
        return (
            str(nearest_row["location_id"]),
            round(min_dist, 1),
            str(nearest_row.get("risk_level", "UNKNOWN")),
            float(nearest_row.get("landslide_probability", 0.0)),
        )

    return None, 0.0, None, 0.0


def load_citizen_reports() -> List[Dict]:
    """Loads all citizen reports from disk."""
    init_storage()
    try:
        with open(CITIZEN_REPORTS_FILE, "r") as f:
            reports = json.load(f)
        return reports
    except Exception as e:
        print(f"Error loading citizen reports: {e}")
        return []


def save_citizen_reports(reports: List[Dict]) -> None:
    """Saves citizen reports list to disk."""
    init_storage()
    with open(CITIZEN_REPORTS_FILE, "w") as f:
        json.dump(reports, f, indent=2)


def add_citizen_report(
    image_file,
    latitude: float,
    longitude: float,
    gps_accuracy_m: float,
    report_type: str,
    description: str,
    latest_risk_df: Optional[pd.DataFrame] = None,
) -> Dict:
    """
    Saves uploaded image, correlates coordinates with nearest AI risk zone,
    and appends new report to storage.
    """
    init_storage()

    report_id = f"REP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    timestamp = datetime.now(timezone.utc).astimezone().isoformat()

    # Save uploaded image
    image_filename = f"{report_id}.jpg"
    image_save_path = CITIZEN_UPLOADS_DIR / image_filename

    if image_file is not None:
        try:
            img = Image.open(image_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            # Resize image if very large to optimize storage and speed
            img.thumbnail((1600, 1600))
            img.save(image_save_path, "JPEG", quality=85)
            rel_image_path = str(image_save_path)
        except Exception as e:
            print(f"Failed to save image: {e}")
            rel_image_path = ""
    else:
        rel_image_path = ""

    # Spatial correlation with nearest AI monitoring grid
    nearest_zone_id, distance_m, zone_risk, zone_prob = find_nearest_monitoring_zone(
        latitude, longitude, latest_risk_df
    )

    new_report = {
        "id": report_id,
        "image_path": rel_image_path,
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "gps_accuracy_m": round(gps_accuracy_m, 1),
        "timestamp": timestamp,
        "report_type": report_type,
        "description": description.strip(),
        "status": STATUS_PENDING,
        "nearest_zone_id": nearest_zone_id or "AIZAWL_GENERAL",
        "distance_to_zone_m": distance_m,
        "zone_risk_level": zone_risk or "UNKNOWN",
        "zone_probability": zone_prob,
    }

    reports = load_citizen_reports()
    reports.insert(0, new_report)  # newest first
    save_citizen_reports(reports)

    return new_report


def update_report_status(report_id: str, new_status: str) -> bool:
    """Updates verification status of a report."""
    reports = load_citizen_reports()
    updated = False
    for r in reports:
        if r["id"] == report_id:
            r["status"] = new_status
            updated = True
            break
    if updated:
        save_citizen_reports(reports)
    return updated
