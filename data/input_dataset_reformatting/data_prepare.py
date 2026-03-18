import os
import pandas as pd
from geopy.distance import geodesic

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
file_name = os.path.join(BASE_DIR, "input_dataset_reformatting", "_roads3.csv")
df = pd.read_csv(file_name)

crossings = [('N1', 'N101'), ('N1', 'N102'), ('N1', 'N104'), ('N1', 'N105'), ('N1', 'N106'), ('N1', 'N107'), ('N1', 'N108'), ('N1', 'N109'), ('N1', 'N110'), ('N1', 'N111')]

for road_a, road_b in crossings:
    road_b_lrp_row = df[(df['lrp'] == 'LRPS') & (df['road'] == road_b)]
    target_lat = road_b_lrp_row['lat'].iloc[0]
    target_lon = road_b_lrp_row['lon'].iloc[0]

    road_a_lrps = df.loc[df['road'] == road_a]

    approx_limit = 0.001
    limit_meters = 100
    target_coords = (target_lat, target_lon)

    close_candidates = road_a_lrps[
        (road_a_lrps['lat'].between(target_coords[0] - approx_limit, target_coords[0] + approx_limit)) &
        (road_a_lrps['lon'].between(target_coords[1] - approx_limit, target_coords[1] + approx_limit))
        ]

    for index, row in close_candidates.iterrows():
        current_coords = (row['lat'], row['lon'])

        # Calculate exact geodesic distance
        dist = geodesic(target_coords, current_coords).meters

        if dist < limit_meters:
            # this is our intersection
            intersection = row
            print(f'Intersection between {road_a} and {road_b}  is at  {intersection}')

            # here you work
            # we need to find in which link from road a is the lrp and then make the lrp in road a have the same id with lrp in road b
            break

