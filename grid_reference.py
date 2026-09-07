"""
Builds the grid_id -> representative (lat, lon) mapping used to drive rainfall
fetches, and the location_id -> grid_id mapping used to broadcast fetched
rainfall back out to all 419 locations.

Why grid-level, not location-level: every grid_id/date pair in the historical
Phase 4 data has byte-identical rainfall across all locations sharing that
grid_id. Phase 4 computed rainfall once per grid cell, not per exact lat/lon.
Fetching per-location would triple-digit multiply API calls for no benefit and
would not match how the training data was generated.
"""
import re
import pandas as pd

_LOCATION_ID_PATTERN = re.compile(r"^(.*)_(-?\d+\.\d+)_(-?\d+\.\d+)$")


def parse_location_id(location_id: str):
    """Split 'AIZ_GRID_040_23.738889_92.696389' into (grid_id, lat, lon)."""
    m = _LOCATION_ID_PATTERN.match(location_id)
    if not m:
        raise ValueError(
            f"location_id '{location_id}' does not match the expected "
            f"'<grid_id>_<lat>_<lon>' format — cannot derive grid_id."
        )
    grid_id, lat, lon = m.groups()
    return grid_id, float(lat), float(lon)


def build_grid_reference(terrain_csv_path: str) -> pd.DataFrame:
    """
    Returns two things joined into location-level rows, plus a grid-level table:

    location_table: location_id, grid_id, latitude, longitude, elevation_m, slope_deg
    grid_table: grid_id, centroid_lat, centroid_lon, n_locations
    """
    terrain = pd.read_csv(terrain_csv_path)
    parsed = terrain["location_id"].apply(parse_location_id)
    terrain["grid_id"] = parsed.apply(lambda t: t[0])

    # Sanity check: the lat/lon embedded in location_id should match the
    # latitude/longitude columns already in the file. If they don't, something
    # is wrong with our parsing assumption — fail loudly rather than silently
    # using the wrong coordinates.
    embedded_lat = parsed.apply(lambda t: t[1])
    embedded_lon = parsed.apply(lambda t: t[2])
    lat_mismatch = (embedded_lat - terrain["latitude"]).abs() > 1e-6
    lon_mismatch = (embedded_lon - terrain["longitude"]).abs() > 1e-6
    if lat_mismatch.any() or lon_mismatch.any():
        bad = terrain.loc[lat_mismatch | lon_mismatch, "location_id"].tolist()
        raise ValueError(
            f"{len(bad)} location_id(s) have embedded coordinates that don't "
            f"match the latitude/longitude columns: {bad[:5]}..."
        )

    grid_table = (
        terrain.groupby("grid_id")
        .agg(
            centroid_lat=("latitude", "mean"),
            centroid_lon=("longitude", "mean"),
            n_locations=("location_id", "count"),
        )
        .reset_index()
    )

    location_table = terrain[
        ["location_id", "grid_id", "latitude", "longitude", "elevation_m", "slope_deg"]
    ].copy()

    return location_table, grid_table


if __name__ == "__main__":
    import sys
    loc_tbl, grid_tbl = build_grid_reference(sys.argv[1] if len(sys.argv) > 1 else "phase9_terrain_input.csv")
    print(f"{len(loc_tbl)} locations across {len(grid_tbl)} grids")
    print(grid_tbl.to_string(index=False))
