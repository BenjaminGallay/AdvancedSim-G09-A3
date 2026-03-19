import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point


def get_intersection_df(roads_preprocessed, roads_shp):

    """
    Given a preprocessed roads DataFrame, finds intersection LRPs by searching for
    'CrossRoad', 'SideRoad' in the 'type' column or 'Intersection' in the 'name' column (case-insensitive, substring match).
    Extracts road names from the 'name' column, matches LRPs between roads, and returns a DataFrame with a 'crossing' column for paired LRP index.
    """
    import re
    roads_csv = roads_preprocessed.copy()
    roads_csv = roads_csv.reset_index(drop=True)
    roads_csv["idx"] = roads_csv.index
    roads_csv["crossing"] = None

    # Helper: extract road names from a string
    def extract_road_names(text):
        if not isinstance(text, str):
            return []
        # Find patterns like N101, N 101, R113, Z1101, R 110, etc.
        pattern = r"([NZR]\s?\d{2,4})"
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        # Also extract inside parentheses (e.g., (R113))
        paren_pattern = r"\(([NZR]\s?\d{2,4})\)"
        matches += re.findall(paren_pattern, text, flags=re.IGNORECASE)
        # Remove duplicates and spaces
        return list(set(m.replace(" ", "") for m in matches))

    # Find intersection candidates
    mask = (
        roads_csv["type"].astype(str).str.contains("crossroad|sideroad", case=False, na=False)
        | roads_csv["name"].astype(str).str.contains("intersection", case=False, na=False)
    )
    intersection_rows = roads_csv[mask].copy()

    # For each intersection row, extract road names from 'name' column
    intersection_rows["intersecting_roads"] = intersection_rows["name"].apply(extract_road_names)

    # Build a mapping from (road, lrp) to idx for fast lookup
    lrp_map = {}
    for i, row in roads_csv.iterrows():
        lrp_map[(str(row["road"]).replace(" ", ""), str(row["lrp"]))] = i

    # For each intersection row, try to find matching LRP(s) on the other road(s)
    for i, row in intersection_rows.iterrows():
        this_road = str(row["road"]).replace(" ", "")
        this_lrp = row["lrp"]
        for other_road in row["intersecting_roads"]:
            # Find candidate rows on the other road that reference this road in their name/type
            candidates = roads_csv[
                (roads_csv["road"].astype(str).str.replace(" ", "") == other_road)
            ]
            # Look for rows that mention this road in their name/type
            found = False
            for j, crow in candidates.iterrows():
                # Check if this road is mentioned in the candidate's name or type
                name_type = str(crow.get("name", "")) + " " + str(crow.get("type", ""))
                if this_road in extract_road_names(name_type):
                    # Mark crossing for both
                    roads_csv.at[i, "crossing"] = crow["idx"]
                    roads_csv.at[j, "crossing"] = row["idx"]
                    found = True
            # If not found, mark the intersection row with the LRP on the other road closest to this LRP (by chainage, then by lat/lon if available)
            if not found and not candidates.empty:
                # Try to use chainage if available
                try:
                    this_lat = float(row.get("lat", np.nan))
                    this_lon = float(row.get("lon", np.nan))
                    dists = (candidates[["lat", "lon"]].astype(float) - [this_lat, this_lon]) ** 2
                    distsum = dists["lat"] + dists["lon"]
                    idx_closest = distsum.idxmin()
                    print(f"Warning: No direct LRP match found for intersection row {i} with road {other_road}. Marking with closest candidate by lat/lon.")
                    #print(row['lat'], row['lon'])
                    #print(candidates.loc[idx_closest]["lat"], candidates.loc[idx_closest]["lon"])
                    roads_csv.at[i, "crossing"] = candidates.loc[idx_closest, "idx"]
                except Exception:
                    # Fallback: just use the first candidate
                    print(f"Warning: No direct LRP match found for intersection row {i} with road {other_road}. Marking with first candidate.")
                    roads_csv.at[i, "crossing"] = candidates.iloc[0]["idx"]

    return roads_csv
