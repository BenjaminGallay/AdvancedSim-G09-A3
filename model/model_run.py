import statistics
import time

import matplotlib.pyplot as plt
import numpy as np
import statistical_recorder

from model import BangladeshModel

"""
    Run simulation
    Print output at terminal
"""

# ---------------------------------------------------------------

# run time 5 x 24 hours; 1 tick 1 minute
# run_length = 5 * 24 * 60

BREAKDOWN_PROBABILITIES = [
    [0, 0, 0, 0],
    [0, 0, 0, 0.05],
    [0, 0, 0.05, 0.1],
    [0, 0.05, 0.1, 0.2],
    [0.05, 0.1, 0.2, 0.4],
]

choice_dict = {
    "0": [0],
    "1": [1],
    "2": [2],
    "3": [3],
    "4": [4],
    "all": range(5),
}

colours = {
    0: "black",
    1: "green",
    2: "yellow",
    3: "orange",
    4: "red",
}
# scenario 0 = no bridges breaking down : baseline travel time. scenario 8 = most likely breakdowns
# run time 7200 ticks = 5*24h runtime
run_length = 7200
number_of_seeds = 10
rand = int(1000000000 * time.time() % 1000000)
seeds = range(rand, rand + number_of_seeds)


# gets the user's choice about the scenario and the statistical/analytical approach
def get_choice():
    valid_choice = False
    print("Select an option :")
    print("- number 0 to 4, runs the corresponding scenario")
    print("- 'all' runs all scenarios successively")

    while not valid_choice:
        choice = input("Enter your choice : ")
        if choice in choice_dict:
            valid_choice = True
        else:
            print("invalid input, please try again")
    scenario_choice = choice_dict[choice]

    valid_choice = False
    print("Select an option :")
    print("1 - Runs an analytical analysis on the network")
    print("2 - Runs a simulation on the network and outputs the statistical values")

    analytical = False
    statistical = False
    while not valid_choice:
        choice = input("Enter your choice : ")
        if choice == "1":
            valid_choice = True
            analytical = True
        elif choice == "2":
            valid_choice = True
            statistical = True
        else:
            print("invalid input, please try again")

    return scenario_choice, statistical, analytical


scenario_choice, statistical, analytical = get_choice()
# takes the statistical/simulation approach
if statistical:
    for scenario in scenario_choice:
        print(f"\n--- Running scenario {scenario} ---")
        statistical_recorder.reset_times()
        for seed in seeds:
            sim_model = BangladeshModel(
                seed=seed, breakdown_probabilities=BREAKDOWN_PROBABILITIES[scenario]
            )
            # Check if the seed is set
            print("SEED " + str(sim_model._seed))

            # One run with given steps
            for i in range(run_length):
                sim_model.step()
        # return the average for all seeds
        ids, travel_times = statistical_recorder.write_to_file_and_return(scenario)
        print(
            "statistical average travel time for scenario",
            scenario,
            ":",
            statistics.mean(travel_times),
        )
        print(
            "total waited time",
            statistical_recorder.get_bridge_waited_time(),
            "minutes",
        )
    sim_model.draw_graph()

# takes the analytical approach, only one Model is build for each scenario, and no need for seed randomization
if analytical:
    for scenario in scenario_choice:
        print(f"\n--- Running scenario {scenario} ---")
        sim_model = BangladeshModel(
            breakdown_probabilities=BREAKDOWN_PROBABILITIES[scenario]
        )
        print("model built")
        # computes the shortest path for each pair of road extremities
        routes = sim_model.get_all_routes()
        lengths, delays = [], []
        for key in routes.keys():
            lengths.append(routes[key][1] / 1000)
            delays.append(routes[key][2])
        plt.plot(
            lengths, delays, "o", c=colours[scenario], label=f"Scenario {scenario}"
        )
        # linear regression
        m, b = np.polyfit(lengths, delays, 1)
        x_line = np.linspace(min(lengths), max(lengths), 100)
        y_line = m * x_line + b
        plt.plot(
            x_line,
            y_line,
            c=colours[scenario],
            label=f"Linear regression for scenario {scenario}, {np.round(m, 1)} minute/km delay",
        )
        plt.xlabel("Path length in kilometers")
        plt.ylabel("Average path delay in minutes")
    plt.legend()
    plt.show()
    sim_model.draw_graph()
