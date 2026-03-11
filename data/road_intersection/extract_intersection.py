import geopandas as gpd
#import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
roads_shp = os.path.join(BASE_DIR, "data", "road_intersection", "road_gis_data", "roads.shp")

# Load OSM road data (update path to your specific file)
roads = gpd.read_file(roads_shp)

#save as xlsx
out_xlsx = os.path.join(BASE_DIR, "data", "road_intersection", "road_gis.xlsx")
roads.to_excel(out_xlsx, index=False)

"""
# intersection extraction

# 1. Project to a local CRS (UTM Zone 45N or 46N for Bangladesh) 
# for geometric accuracy
roads = roads.to_crs(epsg=32646) 

# 2. Perform a Spatial Join to find intersecting lines
# We use a self-join: 'left' and 'right' represent the same dataset
intersections = gpd.sjoin(roads, roads, predicate="intersects", lsuffix="l", rsuffix="r")

# 3. CRITICAL FILTER: Keep only unique pairs
# 'index_r' is the index of the second road. 
# index_l < index_r ensures we only process the pair (A, B) and skip (B, A) and (A, A).
intersections = intersections[intersections.index < intersections['index_r']]

# 4. Extract the actual Point geometry
# The join only tells us THAT they intersect; .intersection() tells us WHERE.
intersections['intersection_point'] = intersections.apply(
    lambda row: row['geometry'].intersection(roads.loc[row['index_r']].geometry), axis=1
)

# 5. Clean up: keep only Point geometries (ignore overlapping lines)
nodes = intersections[intersections['intersection_point'].geom_type == 'Point'].copy()
nodes.set_geometry('intersection_point', inplace=True)

# 6. Drop original road columns to keep it lightweight
nodes = nodes[['osm_id_l', 'osm_id_r', 'name_l', 'name_r', 'intersection_point']]
"""