# Copyright (c) farm-ng, inc.
#
# Licensed under the Amiga Development Kit License (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://github.com/farm-ng/amiga-dev-kit/blob/main/LICENSE
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import argparse
import asyncio
from math import radians
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from farm_ng.track.track_pb2 import Track, TrackFollowerState
from farm_ng.track.utils import TrackBuilder
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.events_file_reader import proto_from_json_file

matplotlib.use("TkAgg")  # Set the backend to Agg for non-GUI environments

# Create a few helper functions to easily create poses and quaternions, and print data


def yaw_to_quaternion(yaw_degrees: float):
    """Convert yaw angle to quaternion
    Args: yaw angle in degrees
    Returns: quaternion (x, y, z, w)"""

    yaw = np.radians(yaw_degrees)

    # Calculate half angle
    yaw_half = yaw * 0.5

    # Calculate quaternion components (only modifying yaw)
    w = np.cos(yaw_half)
    x = 0.0
    y = 0.0
    z = np.sin(yaw_half)

    return np.array([x, y, z, w])


def create_pose(x: float, y: float, heading: float) -> Pose3F64:
    """Create a Pose3F64 from x, y, heading
    Args: x (meters), y (meters), heading (degrees)
    Returns: Pose3F64"""

    # Set the initial pose of the robot
    quaternion = yaw_to_quaternion(heading)
    rotation = Rotation3F64(quaternion.reshape((4, 1)))
    a_from_b = Isometry3F64(rotation=rotation, translation=[x, y, 0.0])

    pose = Pose3F64(
        a_from_b=a_from_b, frame_a="world", frame_b="robot", tangent_of_b_in_a=np.zeros((6, 1), dtype=np.float64)
    )

    return pose


def plot_track(waypoints: list[list[float]], tool_state: dict = {}) -> None:
    x = waypoints[0]
    y = waypoints[1]
    headings = waypoints[2]

    # Calculate the arrow directions
    U = np.cos(headings)
    V = np.sin(headings)

    # Parameters for arrow plotting
    arrow_interval = 25  # Adjust this to change the frequency of arrows
    turn_threshold = np.radians(10)  # Threshold in radians for when to skip plotting

    plt.figure(figsize=(8, 8))
    # plt.plot(x, y, color='orange', linewidth=1.0)

    for i in range(len(x) - 1):
        dot_color = "green" if tool_state.get(i, True) else "red"
        plt.plot(x[i], y[i], marker="o", markersize=1, color=dot_color)

    for i in range(0, len(x), arrow_interval):
        # Calculate the heading change
        if i > 0:
            heading_change = np.abs(headings[i] - headings[i - 1])
        else:
            heading_change = 0

        # Plot the arrow if the heading change is below the threshold
        if heading_change < turn_threshold:
            plt.quiver(x[i], y[i], U[i], V[i], angles='xy', scale_units='xy', scale=1.5, color='blue')

    plt.axis("equal")
    plt.legend(["Track", "Heading"])
    plt.show()


def pack_tool_state(tool_state: dict, track_builder: TrackBuilder(), state: bool) -> dict:
    last_waypoint_index = len(track_builder.track_waypoints)
    for i in range(len(tool_state), last_waypoint_index):
        tool_state[i] = state
    return tool_state


# async def track_follower_subscriber(client: EventClient) -> TrackFollowerState:

async def drive_and_control(config_path, track, tool_state):
    clients: dict[str, EventClient]
    config_list = proto_from_json_file(config_path, EventServiceConfigList())
    expected_configs = ["track_follower", "filter"]
    for config in config_list.configs:
        if config.name in expected_configs:
            clients[config.name] = EventClient(config)
    # Create a track follower client
    
    
    

async def build_track(save_track: bool, reverse: bool) -> (Track, dict):
    """Build a custom track. Here, we will use all the building functions in the TrackBuilder class for educational
    purposes. This specific track will resemble three 60-foot rows spaced 48 inches. To transition from the end of
    the first row to the second, the robot will turn in place 90 degrees. To transition from the end of the second
    row to the third, the robot will perform a smooth u-turn.

    Args:
        save_track: Whether or not to save the track to a file
    """
    print("Building track...")

    last_waypoint_index: int
    tool_state: dict = {}

    # Set the initial pose of the robot
    initial_pose = create_pose(x=5.0, y=10.0, heading=90)

    # Set the second pose of the robot to demonstrate how to create an ab_segment
    second_pose = create_pose(x=25.0, y=10.0, heading=90)

    # Start the track builder
    # track_builder = await TrackBuilder.create(clients=clients, pose=initial_pose)
    track_builder = TrackBuilder(start=initial_pose)
    last_waypoint_index = len(track_builder.track_waypoints) - 1
    tool_state[last_waypoint_index] = True

    # Drive forward from the initial pose to the second pose (about 60 ft)
    track_builder.create_ab_segment("goal1", second_pose)
    # print(f"Length: {len(track_builder.track_waypoints)}")
    tool_state = pack_tool_state(tool_state, track_builder, True)

    # Turn in place 90 degrees
    track_builder.create_turn_segment("goal2", radians(-90))
    # print(f"Length: {len(track_builder.track_waypoints)}")
    tool_state = pack_tool_state(tool_state, track_builder, False)

    # Drive forward 48 inches
    track_builder.create_straight_segment("goal3", 48 * 0.0254)
    tool_state = pack_tool_state(tool_state, track_builder, False)

    # Turn in place 90 degrees
    track_builder.create_turn_segment("goal4", radians(-90))
    tool_state = pack_tool_state(tool_state, track_builder, False)

    # Drive forward 60 feet
    track_builder.create_straight_segment("goal5", 20 - 24 * 0.0254)
    tool_state = pack_tool_state(tool_state, track_builder, True)

    # Smooth turn at the end of the row
    track_builder.create_arc_segment("goal6", 24 * 0.0254, radians(180))
    tool_state = pack_tool_state(tool_state, track_builder, False)

    # Drive forward 60 feet
    track_builder.create_straight_segment("goal7", 20 - 24 * 0.0254)
    last_waypoint_index = len(track_builder.track_waypoints)
    tool_state = pack_tool_state(tool_state, track_builder, True)

    if reverse:
        track_builder.reverse_track()

    # Save the track to a file
    script_path = Path(__file__)  # Current script's path
    parent_directory = script_path.parent
    file_path = parent_directory / "my_track.json"

    if save_track:
        track_builder.save_track(file_path)

    print(f"Tool dict: {tool_state}")

    # Print the number of waypoints in the track
    print(f" Track created with {len(track_builder.track_waypoints)} waypoints")

    # Plot the track
    waypoints = track_builder.unpack_track()
    plot_track(waypoints, tool_state)
    return track_builder.track, tool_state


async def run(args) -> None:
    # Create flag for saving track
    save_track: bool = args.save_track
    reverse: bool = args.reverse

    # Start the asyncio tasks
    tasks: list[asyncio.Task] = [asyncio.create_task(build_track(save_track, reverse))]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-track_follower-square")
    parser.add_argument("--save-track", action='store_true', help="Save the track to a file.")
    parser.add_argument("--reverse", action='store_true', help="Reverse the track.")
    parser.add_argument("--service-config", type=Path, help="Path to the service config file.")
    args = parser.parse_args()

    # Create the asyncio event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
