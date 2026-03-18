import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import LineString, Point

def get_df_out(roads_preprocessed, roads_shp):
    """
    Given a preprocessed roads DataFrame and a roads shapefile GeoDataFrame,
    returns a DataFrame of crossing rows (intersections) to be concatenated to the original roads DataFrame.
    """
    roads_csv = roads_preprocessed.copy()
    roads_csv = roads_csv.reset_index(drop=True)
    roads_csv['idx'] = roads_csv.index
    roads_csv['crossing'] = None
    road_lines = {}
    road_geoms, road_names = [], []
    for road, group in roads_csv.groupby('road'):
        points = [Point(row['lon'], row['lat']) for idx, row in group.iterrows() if not pd.isnull(row['lat']) and not pd.isnull(row['lon'])]
        if len(points) > 1:
            line = LineString(points)
            road_lines[road] = line
            road_geoms.append(line)
            road_names.append(road)

    # Find intersections
    intersections = gpd.sjoin(roads_shp, roads_shp, predicate="intersects", lsuffix="l", rsuffix="r")
    intersections = intersections[intersections.index < intersections['index_r']]
    intersections['intersection_point'] = intersections.apply(
        lambda row: row['geometry'].intersection(roads_shp.loc[row['index_r']].geometry), axis=1
    )
    nodes = intersections[intersections['intersection_point'].geom_type == 'Point'].copy()
    nodes['lat'] = nodes['intersection_point'].apply(lambda p: p.y)
    nodes['lon'] = nodes['intersection_point'].apply(lambda p: p.x)
    nodes = nodes[['lat', 'lon', 'intersection_point']].drop_duplicates().reset_index(drop=True)
    print(f"Identified {len(nodes)} unique intersection points from shapefile.")
    
    def interpolate_chainage_fast(road_lat, road_lon, road_chainage, lat, lon):
        dists = np.sqrt((road_lat - lat)**2 + (road_lon - lon)**2)
        if len(dists) < 2:
            return None
        idx_sorted = np.argsort(dists)[:2]
        i1, i2 = idx_sorted[0], idx_sorted[1]
        ch1, ch2 = road_chainage[i1], road_chainage[i2]
        d1, d2 = dists[i1], dists[i2]
        w = 0.5 if (d1 + d2) == 0 else d2 / (d1 + d2)
        chainage = ch1 * w + ch2 * (1 - w)
        insert_after = min(i1, i2)
        return chainage, insert_after, max(d1, d2), i1

    # Precompute CSV road LineStrings and lat/lon arrays
    csv_road_lines, csv_road_latlon, csv_road_chainage, csv_road_firstrow = {}, {}, {}, {}  
    for road, group in roads_csv.groupby('road'):
        arr_lat = group['lat'].values
        arr_lon = group['lon'].values
        arr_chainage = group['chainage'].values
        points = [Point(lon, lat) for lon, lat in zip(arr_lon, arr_lat) if not np.isnan(lat) and not np.isnan(lon)]
        if len(points) > 1:
            csv_road_lines[road] = LineString(points)
            csv_road_latlon[road] = (arr_lat, arr_lon)
            csv_road_chainage[road] = arr_chainage
            csv_road_firstrow[road] = group.iloc[0]
    print(f"Prepared {len(csv_road_lines)} road geometries from CSV for intersection processing.")
    
    # Efficiently handle all roads within 330m of each intersection, but only one intersection per pair within 100m
    new_rows = []
    intersection_registry = {}
    distance_threshold = 0.003  # ~330m in degrees (approx, at equator)
    dedup_threshold = 0.003     # ~330m in degrees (approx, at equator)

    i = 0
    for idx, intersection in nodes.iterrows():
        i += 1
        if i % 14000 == 0:
            print(f"Processing intersection {i}/{len(nodes)}...")
        point = intersection['intersection_point']
        lat, lon = intersection['lat'], intersection['lon']
        # Find all roads within threshold
        road_distances = [(road, line.distance(point)) for road, line in csv_road_lines.items()]
        close_roads = [road for road, dist in road_distances if dist <= distance_threshold]
        if len(close_roads) < 2:
            continue
        # For all unique pairs of close roads
        for i in range(len(close_roads)):
            for j in range(i+1, len(close_roads)):
                road1, road2 = close_roads[i], close_roads[j]
                pair_key = tuple(sorted([road1, road2]))
                # Check if intersection for this pair exists within 0.003 deg (~100m)
                already = False
                if pair_key in intersection_registry:
                    for prev_lat, prev_lon in intersection_registry[pair_key]:
                        dist = np.sqrt((lat - prev_lat)**2 + (lon - prev_lon)**2)
                        if dist < dedup_threshold:
                            already = True
                            break
                if already:
                    continue
                # Register this intersection
                intersection_registry.setdefault(pair_key, []).append((lat, lon))
                new_idxs, new_rows_pair = [], []
                results = []
                for road in [road1, road2]:
                    arr_lat, arr_lon = csv_road_latlon[road]
                    arr_chainage = csv_road_chainage[road]
                    result = interpolate_chainage_fast(arr_lat, arr_lon, arr_chainage, lat, lon)
                    results.append(result)
                # Only proceed if both roads have valid interpolation and are close enough
                if any(r is None or r[2] > distance_threshold for r in results):
                    continue
                for k, road in enumerate([road1, road2]):
                    chainage, insert_after, max_dist, i1 = results[k]
                    new_idx = roads_csv['idx'].max() + 1 + len(new_rows) + len(new_rows_pair)
                    new_lrp = f"LRP_CROSS_{new_idx}"
                    new_row = csv_road_firstrow[road].copy()
                    new_row['chainage'] = chainage
                    new_row['lat'] = lat
                    new_row['lon'] = lon
                    new_row['lrp'] = new_lrp
                    new_row['idx'] = new_idx
                    new_row['type'] = 'Crossing'
                    new_row['gap'] = ''
                    new_row['bridgedual'] = ''
                    new_row['condition'] = ''
                    new_row['crossing'] = None
                    road_mask = roads_csv['road'] == road
                    idxs = roads_csv[road_mask].index.tolist()
                    insert_pos = idxs[insert_after] + 1 if insert_after < len(idxs) else len(roads_csv)
                    new_rows_pair.append((insert_pos, new_row, road))
                    new_idxs.append(new_idx)
                # Always fill crossing column for both
                new_rows_pair[0][1]['crossing'] = new_idxs[1]
                new_rows_pair[1][1]['crossing'] = new_idxs[0]
                new_rows.extend(new_rows_pair)
    
    # Return DataFrame of new crossing rows
    crossing_rows = [row for _, row, _ in new_rows]
    
    print(f"Generated {len(crossing_rows)} new crossing rows from intersections.")
    if crossing_rows:  
        df_out = pd.Dataframe(crossing_rows)    
    else:
        df_out = pd.DataFrame(columns=roads_csv.columns)

    return df_out