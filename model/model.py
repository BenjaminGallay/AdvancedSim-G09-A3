import os
from collections import defaultdict

import analytical_recorder
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from components import Bridge, Intersection, Link, Sink, Source, SourceSink
from mesa import Model
from mesa.space import ContinuousSpace
from mesa.time import BaseScheduler
from numpy._core.shape_base import block

from model import analytical_recorder


# ---------------------------------------------------------------
def set_lat_lon_bound(lat_min, lat_max, lon_min, lon_max, edge_ratio=0.02):
    """
    Set the HTML continuous space canvas bounding box (for visualization)
    give the min and max latitudes and Longitudes in Decimal Degrees (DD)

    Add white borders at edges (default 2%) of the bounding box
    """

    lat_edge = (lat_max - lat_min) * edge_ratio
    lon_edge = (lon_max - lon_min) * edge_ratio

    x_max = lon_max + lon_edge
    y_max = lat_min - lat_edge
    x_min = lon_min - lon_edge
    y_min = lat_max + lat_edge
    return y_min, y_max, x_min, x_max


# ---------------------------------------------------------------j
class BangladeshModel(Model):
    """
    The main (top-level) simulation model

    One tick represents one minute; this can be changed
    but the distance calculation need to be adapted accordingly

    Class Attributes:
    -----------------
    step_time: int
        step_time = 1 # 1 step is 1 min

    path_ids_dict: defaultdict
        Key: (origin, destination)
        Value: the shortest path (Infra component IDs) from an origin to a destination

        Only straight paths in the Demo are added into the dict;
        when there is a more complex network layout, the paths need to be managed differently

    sources: list
        all sources in the network

    sinks: list
        all sinks in the network

    """

    step_time = 1

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    file_name = os.path.join(BASE_DIR, "data", "roads.csv")

    def __init__(
        self, breakdown_probabilities, seed=None, x_max=500, y_max=500, x_min=0, y_min=0
    ):

        self.schedule = BaseScheduler(self)
        self.running = True
        self.path_ids_dict = defaultdict(lambda: pd.Series())
        self.space = None
        self.sources = []
        self.sinks = []
        self.breakdown_probabilities = breakdown_probabilities
        self.graph = nx.DiGraph()  # We use a directed graph because it offers more possibilities to model if a single side of a bridge breaks for example. It is alos easier to store the list of ids for setting the path using a directed graph

        self.generate_model()

    def generate_model(self):
        """
        generate the simulation model according to the csv file component information

        Warning: the labels are the same as the csv column labels
        """
        df = pd.read_csv(self.file_name)

        # a list of names of roads to be generated
        # TODO You can also read in the road column to generate this list automatically
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

        all_roads = df["road"].unique().tolist()
        n_roads = [road for road in all_roads if road[0] == "N"]
        # roads = ["N1", "N102", "N103"]
        speed = 48 * 1000 / 60

        df_objects_all = []
        for road in roads:
            # Select all the objects on a particular road in the original order as in the cvs
            df_objects_on_road = df[df["road"] == road]

            if not df_objects_on_road.empty:
                df_objects_all.append(df_objects_on_road)

        # put back to df with selected roads so that min and max and be easily calculated
        df = pd.concat(df_objects_all)
        y_min, y_max, x_min, x_max = set_lat_lon_bound(
            df["lat"].min(), df["lat"].max(), df["lon"].min(), df["lon"].max(), 0.05
        )

        # ContinuousSpace from the Mesa package;
        # not to be confused with the SimpleContinuousModule visualization
        self.space = ContinuousSpace(x_max, y_max, True, x_min, y_min)

        # Store the information about the start of the segment of road the program is currently following
        current_edge_start = {"road": None, "id": None}
        current_edge_weight = 0
        current_edge_id_list = []
        current_edge_mean_bridge_delay = 0

        for df in df_objects_all:
            for _, row in df.iterrows():  # index, row in ...
                # create agents according to model_type
                model_type = row["model_type"].strip()
                agent = None

                name = row["name"]
                if pd.isna(name):
                    name = ""
                else:
                    name = name.strip()

                if model_type == "source":
                    agent = Source(row["id"], self, row["length"], name, row["road"])
                    self.sources.append(agent.unique_id)

                    # We add a node corresponding to the element and link it to the previous node if they are on the same road
                    self.graph.add_node(
                        row["id"],
                        road=row["road"],
                        type=model_type,
                        lat=row["lat"],
                        lon=row["lon"],
                    )
                    if current_edge_start["road"] == row["road"]:
                        self.graph.add_edge(
                            current_edge_start["id"],
                            row["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list,
                            mean_delay=current_edge_mean_bridge_delay,
                        )
                        self.graph.add_edge(
                            row["id"],
                            current_edge_start["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list[::-1],
                            mean_delay=current_edge_mean_bridge_delay,
                        )
                    current_edge_start = {"road": row["road"], "id": row["id"]}
                    current_edge_weight = 0
                    current_edge_id_list = []
                    current_edge_mean_bridge_delay = 0

                elif model_type == "sink":
                    agent = Sink(row["id"], self, row["length"], name, row["road"])
                    self.sinks.append(agent.unique_id)

                    # We add a node corresponding to the element and link it to the previous node if they are on the same road
                    self.graph.add_node(
                        row["id"],
                        road=row["road"],
                        type=model_type,
                        lat=row["lat"],
                        lon=row["lon"],
                    )
                    if current_edge_start["road"] == row["road"]:
                        self.graph.add_edge(
                            current_edge_start["id"],
                            row["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list,
                            mean_delay=current_edge_mean_bridge_delay,
                        )
                        self.graph.add_edge(
                            row["id"],
                            current_edge_start["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list[::-1],
                            mean_delay=current_edge_mean_bridge_delay,
                        )
                    current_edge_start = {"road": row["road"], "id": row["id"]}
                    current_edge_weight = 0
                    current_edge_id_list = []
                    current_edge_mean_bridge_delay = 0

                elif model_type == "sourcesink":
                    agent = SourceSink(
                        row["id"], self, row["length"], name, row["road"]
                    )
                    self.sources.append(agent.unique_id)
                    self.sinks.append(agent.unique_id)

                    # We add a node corresponding to the element and link it to the previous node if they are on the same road
                    self.graph.add_node(
                        row["id"],
                        road=row["road"],
                        type=model_type,
                        lat=row["lat"],
                        lon=row["lon"],
                    )
                    if current_edge_start["road"] == row["road"]:
                        self.graph.add_edge(
                            current_edge_start["id"],
                            row["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list,
                            mean_delay=current_edge_mean_bridge_delay,
                        )
                        self.graph.add_edge(
                            row["id"],
                            current_edge_start["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list[::-1],
                            mean_delay=current_edge_mean_bridge_delay,
                        )
                    current_edge_start = {"road": row["road"], "id": row["id"]}
                    current_edge_weight = 0
                    current_edge_id_list = []
                    current_edge_mean_bridge_delay = 0

                elif model_type == "bridge":
                    agent = Bridge(
                        row["id"],
                        self,
                        self.breakdown_probabilities,
                        row["length"],
                        name,
                        row["road"],
                        row["condition"],
                    )
                    current_edge_weight += row["length"]
                    current_edge_id_list.append(row["id"])
                    current_edge_mean_bridge_delay += (
                        analytical_recorder.compute_bridge_mean_delay(row["length"])
                    ) * self.breakdown_probabilities[int(row["condition"])]

                elif model_type == "link":
                    agent = Link(row["id"], self, row["length"], name, row["road"])
                    current_edge_weight += row["length"]
                    current_edge_id_list.append(row["id"])

                elif model_type == "intersection":
                    if not row["id"] in self.schedule._agents:
                        agent = Intersection(
                            row["id"], self, row["length"], name, row["road"]
                        )

                    # Intersection elements are stored in multiple roads, it is necessary to check wether it is already in the graph or not.
                    if row["id"] not in list(self.graph.nodes):
                        self.graph.add_node(
                            row["id"],
                            road={row["road"]},
                            type=model_type,
                            lat=row["lat"],
                            lon=row["lon"],
                        )
                    else:  # if the intersection has already been added from another road
                        self.graph.nodes[row["id"]]["road"].add(row["road"])

                    # We add a node corresponding to the element and link it to the previous node if they are on the same road
                    if current_edge_start["road"] == row["road"]:
                        self.graph.add_edge(
                            current_edge_start["id"],
                            row["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list,
                            mean_delay=current_edge_mean_bridge_delay,
                        )
                        self.graph.add_edge(
                            row["id"],
                            current_edge_start["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list[::-1],
                            mean_delay=current_edge_mean_bridge_delay,
                        )
                    current_edge_start = {"road": row["road"], "id": row["id"]}
                    current_edge_weight = 0
                    current_edge_id_list = []
                    current_edge_mean_bridge_delay = 0

                if agent:
                    self.schedule.add(agent)
                    y = row["lat"]
                    x = row["lon"]
                    self.space.place_agent(agent, (x, y))
                    agent.pos = (x, y)

    # draws the graph of the road network
    def draw_graph(self):
        pos = {n: (d["lon"], d["lat"]) for n, d in self.graph.nodes(data=True)}
        nx.draw_networkx_nodes(self.graph, pos, node_size=50, node_color="pink")
        nx.draw_networkx_edges(self.graph, pos, edge_color="teal", arrows=False)
        plt.show()
        self.check_is_graph_connected()
        return

    # Given a source and a sink, sets the shortest (directed!) path between the two in the path_ids_dict as a list of ids
    def update_path_dict(self, source, sink):
        if not nx.has_path(self.graph, source, sink):
            print("ALLEEEEEEEEEEEEEEEEEEEEEEEEEEEEEERT", source, sink)
        nodes_list = nx.shortest_path(
            self.graph, source=source, target=sink, weight="weight"
        )
        path = []
        route_mean_delay, length = 0, 0
        for i in range(len(nodes_list) - 1):
            path.append(nodes_list[i])
            path += self.graph[nodes_list[i]][nodes_list[i + 1]]["ids"]
            length += self.graph[nodes_list[i]][nodes_list[i + 1]]["weight"]
            route_mean_delay += self.graph[nodes_list[i]][nodes_list[i + 1]][
                "mean_delay"
            ]
        path.append(nodes_list[-1])
        self.path_ids_dict[source, sink] = (path, length, route_mean_delay)
        return

    # gets a random route by choosing a random sink
    def get_random_route(self, source):
        """
        pick up a random route given an origin
        """
        while True:
            # different source and sink
            sink = self.random.choice(self.sinks)
            if sink is not source and nx.has_path(self.graph, source, sink):
                break
        # Ensures that each path is calculated at most once
        if (source, sink) not in self.path_ids_dict:
            self.update_path_dict(source, sink)

        return self.path_ids_dict[source, sink][0]

    # check if the graph is connected (for debugging)
    def check_is_graph_connected(self):
        n1_start = 1000000
        for source in self.sources:
            if not nx.has_path(self.graph, source, n1_start):
                print(
                    f"The {self.graph.nodes[source].get('road')} is not connected to the N1 road"
                )
                continue

    # computes the shortest path for all the pairs of roads extremities
    def get_all_routes(self):
        for source in self.sources:
            for sink in self.sinks:
                if (sink is not source) and nx.has_path(self.graph, source, sink):
                    self.update_path_dict(source, sink)
        return self.path_ids_dict

    # uses the random route choice
    def get_route(self, source):
        return self.get_random_route(source)

    def step(self):
        """
        Advance the simulation by one step.
        """
        self.schedule.step()


# EOF -----------------------------------------------------------
