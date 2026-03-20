import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point


def get_intersection_df(roads_preprocessed, roads_shp):
    # Diagnostics: track referenced roads that could not be paired or created (always uppercase)
    unpaired_references = set()

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

    # Track paired roads for N1 and N2
    paired_roads_N1 = set()
    paired_roads_N2 = set()


    # For each intersection row, duplicate for each intersecting road, assign unique idx, and pair by minimum distance
    new_rows = []
    intersection_points = []
    for i, row in intersection_rows.iterrows():
        this_road = str(row["road"]).replace(" ", "")
        intersecting_roads = row["intersecting_roads"]
        this_lat = float(row.get("lat", np.nan))
        this_lon = float(row.get("lon", np.nan))
        for idx, other_road in enumerate(intersecting_roads):
            other_road = other_road.upper()
            # Track pairing
            if this_road == "N1":
                paired_roads_N1.add(other_road)
            if this_road == "N2":
                paired_roads_N2.add(other_road)

            # Use _dupli{idx} for duplicate LRPs
            lrp_suffix = "_INTER" + (f"_dupli{idx}" if len(intersecting_roads) > 1 else "")
            new_row = row.copy()
            new_row["road"] = this_road
            new_row["lrp"] = str(row["lrp"]) + lrp_suffix
            new_row["type"] = "intersection"
            new_row["crossing"] = None  # Will be set below
            # Assign unique idx for this intersection row
            new_row["idx"] = len(roads_csv) + len(new_rows)
            intersection_points.append((this_road, new_row["idx"], this_lat, this_lon, other_road, new_row["lrp"]))
            new_rows.append(new_row)

    # Add all new intersection rows
    roads_csv = pd.concat([roads_csv, pd.DataFrame(new_rows)], ignore_index=True, sort=False)

    # Now pair intersection rows by minimum distance for each road pair
    intersection_df = roads_csv[roads_csv["type"] == "intersection"].copy()
    # Build lookup for intersection points by road and lrp
    road_points = {}
    for road, idx, lat, lon, other_road, lrp in intersection_points:
        road_points.setdefault(road, []).append((idx, lat, lon, other_road, lrp))

    # For each road pair, pair by minimum distance and ensure unique crossing
    paired = set()
    for road in road_points:
        for idx, lat, lon, other_road, lrp in road_points[road]:
            # Find candidate points on other_road not already paired
            candidates = [t for t in road_points.get(other_road, []) if (t[0], idx) not in paired and (idx, t[0]) not in paired]
            if candidates:
                # Find closest by distance
                dists = [np.sqrt((lat - c[1]) ** 2 + (lon - c[2]) ** 2) for c in candidates]
                min_idx = np.argmin(dists)
                other_idx = candidates[min_idx][0]
                # Set crossing values
                intersection_df.loc[intersection_df["idx"] == idx, "crossing"] = other_idx
                intersection_df.loc[intersection_df["idx"] == other_idx, "crossing"] = idx
                paired.add((idx, other_idx))

    print("Roads paired with N1:", paired_roads_N1)
    print("Roads paired with N2:", paired_roads_N2)

    # Only keep rows where type == 'intersection' and crossing is not None
    intersection_mask = (intersection_df["type"] == "intersection") & (intersection_df["crossing"].notna())
    intersection_rows = intersection_df[intersection_mask].copy()

    # Assign intersection group ids using connected components
    import networkx as nx
    G = nx.Graph()
    for _, row in intersection_rows.iterrows():
        G.add_node(row["idx"])
        if not pd.isna(row["crossing"]):
            G.add_edge(row["idx"], int(row["crossing"]))

    intersection_id_map = {}
    for group_id, component in enumerate(nx.connected_components(G)):
        for idx in component:
            intersection_id_map[idx] = group_id

    intersection_rows["intersection_id"] = intersection_rows["idx"].map(intersection_id_map)

    return intersection_rows


