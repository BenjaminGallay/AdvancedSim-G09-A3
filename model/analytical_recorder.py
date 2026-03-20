mean_travel_delay = 0
road_length = 0
vehicle_speed = 50 * 1000 / 60


# computes the mean delay of a bridge as a function of its length, using the foruma given in the assignment
def compute_bridge_mean_delay(length):
    if length < 10:
        mean_delay = 15
    elif length < 50:
        mean_delay = 37.5
    elif length < 200:
        mean_delay = 67.5
    else:
        mean_delay = (
            7 / 3
        ) * 60  # expected value of the triangular distribution of probability

    return mean_delay


def get_expected_mean_travel_time():
    return mean_travel_delay + road_length / vehicle_speed
