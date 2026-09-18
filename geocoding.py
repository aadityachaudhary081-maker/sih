"""
NEXORA Reverse Geocoding & Locality Intelligence Engine
Resolves (latitude, longitude) coordinates to real human-readable localities,
neighborhoods, and cities using free reverse geocoding APIs (BigDataCloud + OpenStreetMap Nominatim)
with local JSON caching for instant subsequent lookups.
"""

import json
import math
from pathlib import Path
from typing import Dict, Tuple, Optional

import requests
import pandas as pd

DATA_DIR = Path("data")
GEOCODE_CACHE_FILE = DATA_DIR / "geocode_cache.json"

# Prominent Aizawl Landmark Centroids for local fallback
AIZAWL_LOCALITY_CENTROIDS = [
    ("Chaltlang Ridge", 23.7535, 92.7230),
    ("Durtlang Heights", 23.7780, 92.7420),
    ("Bawngkawn North", 23.7570, 92.7350),
    ("Zemabawk East", 23.7510, 92.7580),
    ("Chanmari Central", 23.7440, 92.7200),
    ("Tuikual South", 23.7320, 92.7150),
    ("Mission Veng", 23.7180, 92.7180),
    ("Kulikawn South", 23.7050, 92.7150),
    ("Khatla West", 23.7250, 92.7080),
    ("Tlangnuam Sector", 23.7388, 92.6963),
    ("Bethlehem Veng", 23.7310, 92.7350),
    ("Ramhlun North", 23.7520, 92.7290),
    ("Tanhril (MZU Zone)", 23.7350, 92.6650),
    ("Sairang Valley", 23.8050, 92.6580),
    ("Falkawn District", 23.6350, 92.7120),
    ("Sihphir East", 23.8150, 92.7500),
    ("Luangmual Industrial", 23.7450, 92.6850),
    ("Salem Veng", 23.7150, 92.7300),
    ("Armed Veng", 23.7380, 92.7380),
    ("Zarkawt Central", 23.7390, 92.7180),
]


def _load_cache() -> Dict[str, str]:
    if GEOCODE_CACHE_FILE.exists():
        try:
            with open(GEOCODE_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache: Dict[str, str]):
    DATA_DIR.mkdir(exist_ok=True)
    try:
        with open(GEOCODE_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Failed to save geocode cache: {e}")


def _haversine_dist_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_nearest_landmark_name(lat: float, lon: float) -> Optional[str]:
    """Matches coordinates with closest Aizawl municipal/topographic landmark."""
    best_name = None
    min_dist = float("inf")

    for name, c_lat, c_lon in AIZAWL_LOCALITY_CENTROIDS:
        dist = _haversine_dist_km(lat, lon, c_lat, c_lon)
        if dist < min_dist:
            min_dist = dist
            best_name = name

    if min_dist <= 1.0:
        return f"{best_name}, Aizawl"
    elif min_dist <= 3.5:
        return f"Near {best_name}, Aizawl"
    elif min_dist <= 12.0:
        return f"{best_name} Sector ({min_dist:.1f}km), Aizawl"

    return None


def fetch_ip_geolocation(timeout_s: int = 3) -> Optional[Dict[str, float]]:
    """Fetches approximate client GPS coordinates via free IP geolocation APIs."""
    # 1. ipwho.is
    try:
        r = requests.get("https://ipwho.is/", timeout=timeout_s)
        if r.status_code == 200:
            d = r.json()
            if d.get("success", True) and "latitude" in d and "longitude" in d:
                return {
                    "latitude": float(d["latitude"]),
                    "longitude": float(d["longitude"]),
                    "accuracy": 25.0,
                    "city": d.get("city", ""),
                    "region": d.get("region", ""),
                }
    except Exception:
        pass

    # 2. ipapi.co
    try:
        r = requests.get("https://ipapi.co/json/", timeout=timeout_s)
        if r.status_code == 200:
            d = r.json()
            if "latitude" in d and "longitude" in d:
                return {
                    "latitude": float(d["latitude"]),
                    "longitude": float(d["longitude"]),
                    "accuracy": 35.0,
                    "city": d.get("city", ""),
                    "region": d.get("region_name") or d.get("region", ""),
                }
    except Exception:
        pass

    return None


def reverse_geocode_online(lat: float, lon: float, timeout_s: int = 4) -> Optional[str]:
    """Queries free BigDataCloud / OSM Nominatim reverse geocoding API for exact locality name."""
    # 1. BigDataCloud free client geocoding (fastest, high detail)
    try:
        url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=en"
        resp = requests.get(url, timeout=timeout_s)
        if resp.status_code == 200:
            data = resp.json()
            locality = data.get("locality") or data.get("city")
            subdivision = data.get("principalSubdivision") or ""
            admin_info = data.get("localityInfo", {}).get("administrative", [])
            sub_locality = ""
            for item in admin_info:
                name = item.get("name", "")
                if item.get("adminLevel") in (6, 7, 8) and "block" not in name.lower() and name != locality:
                    sub_locality = name
                    break
            parts = [p for p in [sub_locality, locality, subdivision] if p]
            if parts:
                return ", ".join(parts[:2]) if len(parts) >= 2 else parts[0]
    except Exception:
        pass

    # 2. OpenStreetMap Nominatim fallback
    try:
        url_osm = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "NEXORA-Disaster-Intelligence-Platform/1.0"}
        resp = requests.get(url_osm, headers=headers, timeout=timeout_s)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("village") or addr.get("county") or addr.get("subdistrict")
            city = addr.get("city") or addr.get("town") or addr.get("state_district")
            state = addr.get("state")
            parts = [p for p in [suburb, city, state] if p]
            if parts:
                return ", ".join(parts[:2])
    except Exception:
        pass

    return None


def search_osm_locations(query: str, limit: int = 6, timeout_s: int = 4) -> list:
    """
    Searches places matching query using local Aizawl centroids + OpenStreetMap Nominatim API.
    Returns list of dicts: [{'display_name': ..., 'lat': ..., 'lon': ...}]
    """
    if not query or len(query.strip()) < 2:
        return []

    q_clean = query.strip().lower()
    results = []
    seen_coords = set()

    # 1. Match local high-precision Aizawl centroids
    for name, c_lat, c_lon in AIZAWL_LOCALITY_CENTROIDS:
        if q_clean in name.lower() or any(word in name.lower() for word in q_clean.split()):
            coord_key = (round(c_lat, 4), round(c_lon, 4))
            if coord_key not in seen_coords:
                seen_coords.add(coord_key)
                results.append({
                    "display_name": f"📍 {name}, Aizawl, Mizoram",
                    "lat": float(c_lat),
                    "lon": float(c_lon),
                    "type": "landmark",
                })

    # 2. Query OpenStreetMap Nominatim with Aizawl context and viewbox
    try:
        search_queries = [
            f"{query.strip()}, Aizawl, Mizoram",
            query.strip(),
        ]
        headers = {"User-Agent": "NEXORA-Disaster-Intelligence-Platform/1.0 (contact: disaster-cell@mizoram.gov.in)"}

        for sq in search_queries:
            if len(results) >= limit:
                break
            url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(sq)}&format=json&addressdetails=1&viewbox=92.5,23.9,92.9,23.6&limit={limit}&countrycodes=in"
            resp = requests.get(url, headers=headers, timeout=timeout_s)
            if resp.status_code == 200:
                for item in resp.json():
                    lat = float(item.get("lat"))
                    lon = float(item.get("lon"))
                    coord_key = (round(lat, 4), round(lon, 4))
                    if coord_key not in seen_coords:
                        seen_coords.add(coord_key)
                        results.append({
                            "display_name": item.get("display_name", ""),
                            "lat": lat,
                            "lon": lon,
                            "type": item.get("type", "location"),
                        })
    except Exception as e:
        print(f"OSM search error: {e}")

    return results[:limit]


def get_location_name(lat: float, lon: float, use_api: bool = True) -> str:
    """
    Returns exact human-readable location name for given (lat, lon).
    Uses high-speed local cache -> Free Online API -> Aizawl landmark matching -> coordinate fallback.
    """
    cache_key = f"{lat:.4f}_{lon:.4f}"
    cache = _load_cache()

    if cache_key in cache:
        return cache[cache_key]

    # Try online API first when enabled
    if use_api:
        api_name = reverse_geocode_online(lat, lon)
        if api_name:
            cache[cache_key] = api_name
            _save_cache(cache)
            return api_name

    # Check local Aizawl landmarks fallback
    landmark_name = get_nearest_landmark_name(lat, lon)
    if landmark_name:
        cache[cache_key] = landmark_name
        _save_cache(cache)
        return landmark_name

    # Fallback to exact coordinates
    coord_fallback = f"{lat:.4f}° N, {lon:.4f}° E"
    cache[cache_key] = coord_fallback
    _save_cache(cache)
    return coord_fallback


def format_location_display(lat: float, lon: float) -> str:
    """Returns a full display string combining locality name and coordinates."""
    loc_name = get_location_name(lat, lon, use_api=True)
    if "°" in loc_name:
        return f"📍 {loc_name}"
    return f"📍 {loc_name} ({lat:.4f}° N, {lon:.4f}° E)"


def enrich_with_location_names(df: pd.DataFrame) -> pd.DataFrame:
    """Enriches a DataFrame with human-readable 'location_name' column."""
    if df.empty or "latitude" not in df.columns or "longitude" not in df.columns:
        return df

    if "location_name" in df.columns and df["location_name"].notna().all():
        return df

    df = df.copy()
    names = []
    for _, row in df.iterrows():
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        name = get_location_name(lat, lon, use_api=True)
        names.append(name)

    df["location_name"] = names
    return df


def is_within_mizoram(lat: float, lon: float, loc_name: str = "") -> bool:
    """
    Checks if given coordinates / locality fall within Aizawl District monitoring jurisdiction.
    Aizawl District approximate bounding box:
        Latitude: 23.55°N – 24.05°N
        Longitude: 92.55°E – 92.90°E
    Reports outside this zone are blocked.
    """
    # Aizawl district bounding box (tighter than all of Mizoram)
    in_aizawl_bbox = (23.55 <= lat <= 24.05) and (92.55 <= lon <= 92.90)

    if loc_name:
        loc_lower = loc_name.lower()
        # Explicit Aizawl / Mizoram mention → always allow
        if "aizawl" in loc_lower:
            return True
        # If within bbox but resolved to a non-Mizoram state → block
        other_states = [
            "gujarat", "surat", "delhi", "maharashtra", "mumbai", "karnataka", "bengaluru",
            "tamil nadu", "chennai", "rajasthan", "punjab", "haryana", "uttar pradesh",
            "bihar", "west bengal", "kolkata", "kerala", "odisha", "telangana", "hyderabad",
            "andhra pradesh", "madhya pradesh", "assam", "tripura", "manipur", "meghalaya",
            "mizoram",  # allow only aizawl district, not all of mizoram
        ]
        # Remove mizoram from block list — we want to allow it if bbox also matches
        non_aizawl_mizoram = [s for s in other_states if s != "mizoram"]
        if any(st_name in loc_lower for st_name in non_aizawl_mizoram):
            return False

    return in_aizawl_bbox
