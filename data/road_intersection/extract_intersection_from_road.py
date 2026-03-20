import os

import pandas as pd
from geopy.distance import geodesic


# returns the dataframe with detected intersections
def get_intersection_df(menfou, balec):
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
        "N2",
        "N203",
        "N204",
        "N205",
        "N206",
        "N207",
        "N208",
        "N209",
        "N210",
    ]
    # tells which are the main roads, and wich are side roads
    road_structure = {
        "N1": [road for road in roads if road[:2] == "N1" and road != "N1"] + ["N2"],
        "N102": ["N103"],
        "N2": [road for road in roads if road[:2] == "N2" and road != "N2"]
        + [road for road in roads if road[:2] == "N1" and road != "N1"],
    }

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    file_name = os.path.join(BASE_DIR, "input_dataset_reformatting", "_roads3.csv")
    df = pd.read_csv(file_name)
    # columns of the output dataframe
    columns = [
        "road",
        "chainage",
        "lrp",
        "lat",
        "lon",
        "gap",
        "type",
        "name",
        "condition",
        "bridgedual",
        "idx",
        "crossing",
    ]
    counter = 123456789
    df_out = pd.DataFrame(columns=columns)
    for main_road in road_structure.keys():
        main_df = df[df["road"] == main_road]
        # runs the algorithm once for roads starts and once for roads ends
        for lrp in ["LRPS", "LRPE"]:
            df_start_ends_side_roads = df[
                df["road"].isin(road_structure[main_road]) & (df["lrp"] == lrp)
            ]
            # stores the closest points for all the side roads to their main road
            closest_points = {
                road: {
                    "distance": 100000000000000000000,
                    "lrp_main": "",
                    "chainage_main": 0,
                    "lat_main": 0,
                    "lon_main": 0,
                    "lrp_side": "",
                    "chainage_side": 0,
                    "lat_side": 0,
                    "lon_side": 0,
                }
                for road in road_structure[main_road]
            }
            # print(closest_points)
            for _, main_row in main_df.iterrows():
                for _, side_row in df_start_ends_side_roads.iterrows():
                    distance = geodesic(
                        (main_row["lat"], main_row["lon"]),
                        (side_row["lat"], side_row["lon"]),
                    )
                    # updates the closest points if the distance is lower than the previous one
                    if distance < closest_points[side_row["road"]]["distance"]:
                        closest_points[side_row["road"]] = {
                            "distance": distance,
                            "lrp_main": main_row["lrp"],
                            "chainage_main": float(main_row["chainage"]),
                            "lat_main": float(main_row["lat"]),
                            "lon_main": float(main_row["lon"]),
                            "lrp_side": side_row["lrp"],
                            "chainage_side": float(side_row["chainage"]),
                            "lat_side": float(side_row["lat"]),
                            "lon_side": float(side_row["lon"]),
                        }
            for road in road_structure[main_road]:
                # threshold of 5kms (explained in the report)
                if closest_points[road]["distance"] < 5:
                    # writes to the dataframe
                    df_out.loc[len(df_out)] = {
                        "road": main_road,
                        "chainage": float(closest_points[road]["chainage_main"]),
                        "lrp": closest_points[road]["lrp_main"],
                        "lat": closest_points[road]["lat_main"],
                        "lon": closest_points[road]["lon_main"],
                        "gap": "",
                        "type": "Crossing",
                        "name": "New crossing yepeeee",
                        "condition": "",
                        "bridgedual": "",
                        "idx": counter,
                        "crossing": counter + 1,
                    }
                    df_out.loc[len(df_out)] = {
                        "road": road,
                        "chainage": float(closest_points[road]["chainage_side"]),
                        "lrp": closest_points[road]["lrp_side"],
                        "lat": closest_points[road]["lat_side"],
                        "lon": closest_points[road]["lon_side"],
                        "gap": "",
                        "type": "Crossing",
                        "name": "New crossing yepeeee",
                        "condition": "",
                        "bridgedual": "",
                        "idx": counter + 1,
                        "crossing": counter,
                    }
                    counter += 2
    return df_out
