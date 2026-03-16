

import geopandas as gpd
import pandas as pd
import numpy as np
import os
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

import matplotlib.pyplot as plt


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
roads_shp_path = os.path.join(BASE_DIR, "data", "road_intersection", "road_gis_data", "roads.shp")
roads_csv_path = os.path.join(BASE_DIR, "data","roads_int.csv")

roads_shp = gpd.read_file(roads_shp_path)
roads_shp = roads_shp.drop(columns=["osm_id", "type", "ref", "oneway", "bridge", "maxspeed"])
roads_shp = roads_shp.to_crs(epsg=4326)

# Load CSV and add idx column
roads_csv = pd.read_csv(roads_csv_path)
roads_csv = roads_csv.reset_index(drop=True)
roads_csv['idx'] = roads_csv.index
# Ensure lrp column exists (if not, create from row order per road)
if 'lrp' not in roads_csv.columns:
    roads_csv['lrp'] = None
# Ensure crossing column exists
if 'crossing' not in roads_csv.columns:
    roads_csv['crossing'] = None
print("Files loaded")

road_lines = {}
road_geoms = []
road_names = []
for road, group in roads_csv.groupby('road'):
    points = [Point(row['lon'], row['lat']) for idx, row in group.iterrows() if not pd.isnull(row['lat']) and not pd.isnull(row['lon'])]
    if len(points) > 1:
        line = LineString(points)
        road_lines[road] = line
        road_geoms.append(line)
        road_names.append(road)

print(f"Created {len(road_lines)} road LineStrings from CSV.")

# Build spatial index for fast nearest search
strtree = STRtree(road_geoms)

##########   Find intersections
# Spatial join to find intersections
intersections = gpd.sjoin(roads_shp, roads_shp, predicate="intersects", lsuffix="l", rsuffix="r")
intersections = intersections[intersections.index < intersections['index_r']]
intersections['intersection_point'] = intersections.apply(
    lambda row: row['geometry'].intersection(roads_shp.loc[row['index_r']].geometry), axis=1
)
nodes = intersections[intersections['intersection_point'].geom_type == 'Point'].copy()
nodes['lat'] = nodes['intersection_point'].apply(lambda p: p.y)
nodes['lon'] = nodes['intersection_point'].apply(lambda p: p.x)
nodes = nodes[['lat', 'lon', 'intersection_point']].drop_duplicates().reset_index(drop=True)
print(f"Intersections computed: {len(nodes)}")

############ Place intersections



# --- Fast intersection placement ---
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
csv_road_lines = {}
csv_road_latlon = {}
csv_road_chainage = {}
csv_road_firstrow = {}
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

new_rows = []
i = 0
for idx, intersection in nodes.iterrows():
    i += 1
    if i % 10000 == 0:
        print(f"Processing intersection {i}/{len(nodes)}...")
    point = intersection['intersection_point']
    lat, lon = intersection['lat'], intersection['lon']
    # Find closest roads
    road_distances = [(road, line.distance(point)) for road, line in csv_road_lines.items()]
    road_distances = sorted(road_distances, key=lambda x: x[1])
    if len(road_distances) < 2:
        continue
    (road1, d1), (road2, d2) = road_distances[:2]
    if d1 > 0.001 or d2 > 0.001:
        continue
    new_idxs = []
    print(f"Processing intersection {idx} at ({lat:.6f}, {lon:.6f}) between {road1} and {road2}")
    for road in [road1, road2]:
        arr_lat, arr_lon = csv_road_latlon[road]
        arr_chainage = csv_road_chainage[road]
        result = interpolate_chainage_fast(arr_lat, arr_lon, arr_chainage, lat, lon)
        if result is None:
            continue
        chainage, insert_after, max_dist, i1 = result
        if max_dist > 0.001:
            continue
        new_idx = roads_csv['idx'].max() + 1 + len(new_rows)
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
        # Insert after insert_after in the full DataFrame
        road_mask = roads_csv['road'] == road
        idxs = roads_csv[road_mask].index.tolist()
        insert_pos = idxs[insert_after] + 1 if insert_after < len(idxs) else len(roads_csv)
        new_rows.append((insert_pos, new_row, road))
        new_idxs.append(new_idx)
    if len(new_idxs) == 2:
        new_rows[-2][1]['crossing'] = new_idxs[1]
        new_rows[-1][1]['crossing'] = new_idxs[0]

print(f"Inserting new rows for intersections... : {len(new_rows)}")
# Insert new rows into DataFrame
for insert_pos, new_row, road in sorted(new_rows, key=lambda x: x[0], reverse=True):
    # Insert into the correct position for the road
    mask = (roads_csv['road'] == road)
    idxs = roads_csv[mask].index.tolist()
    if insert_pos >= len(idxs):
        # Append at end
        roads_csv = pd.concat([roads_csv, pd.DataFrame([new_row])], ignore_index=True)
    else:
        before = roads_csv.iloc[:idxs[insert_pos]]
        after = roads_csv.iloc[idxs[insert_pos]:]
        roads_csv = pd.concat([before, pd.DataFrame([new_row]), after], ignore_index=True)

# --- Plot N1 and intersections ---

plt.figure(figsize=(12, 8))
# Plot N1 as thick blue line
n1_points = roads_csv[roads_csv['road'] == 'N1']
plt.plot(n1_points['lon'], n1_points['lat'], label='N1 (Big Road)', color='blue', linewidth=2)

n2_points = roads_csv[roads_csv['road'] == 'N2']
plt.plot(n2_points['lon'], n2_points['lat'], label='N2 (Big Road)', color='blue', linewidth=2)

# Plot N101-N109 as thin green lines
for road_num in range(101, 109):
    road_name = f'N{road_num}'
    road_points = roads_csv[roads_csv['road'] == road_name]
    if not road_points.empty:
        plt.plot(road_points['lon'], road_points['lat'], label=road_name, color='green', linewidth=1)

# Plot N201-N203 as thin green lines
for road_num in range(201, 203):
    road_name = f'N{road_num}'
    road_points = roads_csv[roads_csv['road'] == road_name]
    if not road_points.empty:
        plt.plot(road_points['lon'], road_points['lat'], label=road_name, color='green', linewidth=1)

# Plot intersection points as red dots
plt.scatter(nodes['lon'], nodes['lat'], color='red', s=3, label='Intersections')

plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('N1 (Big Road) and N101-N109 (Small Roads) with Intersections')
plt.legend()
plt.grid(True)
plt.show()


print(roads_csv.head())
# Save modified roads_csv
roads_csv_out_path = os.path.join(BASE_DIR, "data", "roads_intersection.csv")
roads_csv.to_csv(roads_csv_out_path, index=False)