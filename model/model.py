import os
from collections import defaultdict

import networkx as nx
import pandas as pd
from components import Bridge, Intersection, Link, Sink, Source, SourceSink
from mesa import Model
from mesa.space import ContinuousSpace
from mesa.time import BaseScheduler


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


# ---------------------------------------------------------------
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
    file_name = os.path.join(BASE_DIR, "data", "demo-4-numerical.csv")

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
        roads = ["N1", "N2"]

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
                    self.graph.add_node(row["id"], road=row["road"], type=model_type)
                    if current_edge_start["road"] == row["road"]:
                        self.graph.add_edge(
                            current_edge_start["id"],
                            row["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list,
                        )
                        self.graph.add_edge(
                            row["id"],
                            current_edge_start["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list[::-1],
                        )
                    current_edge_start = {"road": row["road"], "id": row["id"]}
                    current_edge_weight = 0
                    current_edge_id_list = []

                elif model_type == "sink":
                    agent = Sink(row["id"], self, row["length"], name, row["road"])
                    self.sinks.append(agent.unique_id)

                    # We add a node corresponding to the element and link it to the previous node if they are on the same road
                    self.graph.add_node(row["id"], road=row["road"], type=model_type)
                    if current_edge_start["road"] == row["road"]:
                        self.graph.add_edge(
                            current_edge_start["id"],
                            row["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list,
                        )
                        self.graph.add_edge(
                            row["id"],
                            current_edge_start["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list[::-1],
                        )
                    current_edge_start = {"road": row["road"], "id": row["id"]}
                    current_edge_weight = 0
                    current_edge_id_list = []

                elif model_type == "sourcesink":
                    agent = SourceSink(
                        row["id"], self, row["length"], name, row["road"]
                    )
                    self.sources.append(agent.unique_id)
                    self.sinks.append(agent.unique_id)

                    # We add a node corresponding to the element and link it to the previous node if they are on the same road
                    self.graph.add_node(row["id"], road=row["road"], type=model_type)
                    if current_edge_start["road"] == row["road"]:
                        self.graph.add_edge(
                            current_edge_start["id"],
                            row["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list,
                        )
                        self.graph.add_edge(
                            row["id"],
                            current_edge_start["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list[::-1],
                        )
                    current_edge_start = {"road": row["road"], "id": row["id"]}
                    current_edge_weight = 0
                    current_edge_id_list = []

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
                            row["id"], road=[row["road"]], type=model_type
                        )
                    else:  # if the intersection has already been added from another road
                        self.graph.nodes[row["id"]]["road"].append(row["road"])

                    # We add a node corresponding to the element and link it to the previous node if they are on the same road
                    if current_edge_start["road"] == row["road"]:
                        self.graph.add_edge(
                            current_edge_start["id"],
                            row["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list,
                        )
                        self.graph.add_edge(
                            row["id"],
                            current_edge_start["id"],
                            weight=current_edge_weight,
                            ids=current_edge_id_list[::-1],
                        )
                    current_edge_start = {"road": row["road"], "id": row["id"]}
                    current_edge_weight = 0
                    current_edge_id_list = []

                if agent:
                    self.schedule.add(agent)
                    y = row["lat"]
                    x = row["lon"]
                    self.space.place_agent(agent, (x, y))
                    agent.pos = (x, y)

    # Given a source and a sink, sets the shortest (directed!) path between the two in the path_ids_dict as a list of ids
    def update_path_dict(self, source, sink):
        nodes_list = nx.shortest_path(
            self.graph, source=source, target=sink, weight="weight"
        )
        path = []
        for i in range(len(nodes_list) - 1):
            path.append(nodes_list[i])
            path += self.graph[nodes_list[i]][nodes_list[i + 1]]["ids"]
        path.append(nodes_list[-1])
        # print("I'm adding the path", path)
        self.path_ids_dict[source, sink] = path
        return

    def get_random_route(self, source):
        """
        pick up a random route given an origin
        """
        while True:
            # different source and sink
            sink = self.random.choice(self.sinks)
            if sink is not source:
                break
        # Ensures that each path is calculated at most once
        if (source, sink) not in self.path_ids_dict:
            self.update_path_dict(source, sink)
        return self.path_ids_dict[source, sink]

    # TODO
    def get_route(self, source):
        return self.get_random_route(source)

    def step(self):
        """
        Advance the simulation by one step.
        """
        self.schedule.step()


# EOF -----------------------------------------------------------
