import os

import pandas as pd
from geopy.distance import geodesic

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
file_name = os.path.join(BASE_DIR, "input_dataset_reformatting", "_roads3.csv")
df = pd.read_csv(file_name)

roads = [
    "N1",
    "N101",
    "N102",
    "N103",
    "N104",
    "N105",
    "N106",
    "N107",
    "N108",
    "N109",
    "N110",
    "N111",
    "N112",
    "N119",
    "N120",
    "N123",
    "N128",
    "N129",
]
df_list = []
for road_name in roads:
    temp_df = df[df["road"] == road_name]
    df_list.append(temp_df)

crossings = []

for i in range(len(df_list)):
    df1 = df_list[i]
    for j in range(i + 1, len(df_list)):
        df2 = df_list[j]
        min_distance = 10000000000000000000
        for _, row2 in df2.iterrows():
            for _, row1 in df1.iterrows():
                distance = geodesic(
                    (row1["lat"], row1["lon"]), (row2["lat"], row2["lon"])
                )
                if distance < min_distance:
                    # print(distance, row1["lrp"], row2["lrp"])
                    min_distance = distance
                if distance < 0.1:
                    break
            if min_distance < 0.1:
                break
        print(f"min distance for roads {roads[i]} and {roads[j]} is {min_distance}")
        if min_distance < 1:
            crossings.append((roads[i], roads[j]))

print(crossings)
