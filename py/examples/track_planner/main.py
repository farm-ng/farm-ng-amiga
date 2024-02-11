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
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.track.track_pb2 import Track
from farm_ng.track.utils import TrackBuilder

matplotlib.use("TkAgg")  # Set the backend to Agg for non-GUI environments

# Create a helper functions to print data


def plot_track(waypoints: list[list[float]]) -> None:
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
    plt.plot(x, y, color='orange', linewidth=1.0)

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


async def build_track(save_track: bool, reverse: bool, clients: dict | None = None) -> (Track, dict):
    """Build a custom track. Here, we will use all the building functions in the TrackBuilder class for educational
    purposes. This specific track will resemble three 60-foot rows spaced 48 inches. To transition from the end of
    the first row to the second, the robot will turn in place 90 degrees. To transition from the end of the second
    row to the third, the robot will perform a smooth u-turn.

    Args:
        save_track: Whether or not to save the track to a file
    """
    print("Building track...")

    row_spacing = 48 * 0.0254  # 48 inches in meters
    row_length = 35 * 6 * 0.0254  # 60 feet in meters

    # Path: Start at 2, up 2, down 4, up 1, down 3, up 1, down 4, line up to 2

    # Start the track builder
    track_builder = await TrackBuilder.create(clients=clients)
    # Drive forward 20 ft (up 2)
    track_builder.create_straight_segment(next_frame_b="goal1", distance=row_length, spacing=0.1)

    # Maneuver at the end of row: skip one row (96 inches) - (go to 4)
    track_builder.create_arc_segment(next_frame_b="goal2", radius=row_spacing, angle=radians(180), spacing=0.1)

    # Drive forward 20 ft (down 4)
    track_builder.create_straight_segment(next_frame_b="goal3", distance=row_length, spacing=0.1)

    # # Maneuver at the end of row: skip one row (96 inches) - (go to 1)
    track_builder.create_arc_segment(next_frame_b="goal4", radius=1.5 * row_spacing, angle=radians(180), spacing=0.1)

    # Drive forward 20 ft (up 1)
    track_builder.create_straight_segment(next_frame_b="goal5", distance=row_length, spacing=0.1)

    # Maneuver at the end of row: skip one row (96 inches) - (go to 3)
    track_builder.create_arc_segment(next_frame_b="goal6", radius=row_spacing, angle=radians(180), spacing=0.1)

    # Drive forward 20 ft (down 3)
    track_builder.create_straight_segment(next_frame_b="goal7", distance=row_length, spacing=0.1)

    # Maneuver at the end of row: skip one row (96 inches) - (go to 1)
    track_builder.create_arc_segment(next_frame_b="goal8", radius=row_spacing, angle=radians(180), spacing=0.1)

    # Drive forward 20 ft (up 1)
    track_builder.create_straight_segment(next_frame_b="goal9", distance=row_length, spacing=0.1)

    # Maneuver at the end of row: skip one row (96 inches) - (go to 4)
    track_builder.create_arc_segment(next_frame_b="goal10", radius=1.5 * row_spacing, angle=radians(180), spacing=0.1)

    # Drive forward 20 ft (down 4)
    track_builder.create_straight_segment(next_frame_b="goal11", distance=row_length, spacing=0.1)

    # Maneuver at the end of row: skip one row (96 inches) - (go to 2)
    track_builder.create_arc_segment(next_frame_b="goal12", radius=row_spacing, angle=radians(170), spacing=0.1)

    if reverse:
        track_builder.reverse_track()

    # Save the track to a file
    script_path = Path(__file__)  # Current script's path
    parent_directory = script_path.parent
    file_path = parent_directory / "WAE_strawberry.json"

    if save_track:
        track_builder.save_track(file_path)

    # Print the number of waypoints in the track
    print(f" Track created with {len(track_builder.track_waypoints)} waypoints")

    # Plot the track
    waypoints = track_builder.unpack_track()
    plot_track(waypoints)
    return track_builder.track


async def run(args) -> None:
    # Create flag for saving track
    save_track: bool = args.save_track
    reverse: bool = args.reverse

    if args.service_config is not None:
        clients: dict[str, EventClient] = {}
        expected_configs = ["filter"]
        config_list = proto_from_json_file(args.service_config, EventServiceConfigList())
        for config in config_list.configs:
            if config.name in expected_configs:
                clients[config.name] = EventClient(config)

        # Confirm that EventClients were created for all required services
        for config in expected_configs:
            if config not in clients:
                raise RuntimeError(f"No {config} service config in {args.service_config}")
    else:
        clients = None

    # Start the asyncio tasks
    tasks: list[asyncio.Task] = [asyncio.create_task(build_track(save_track, reverse, clients))]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-track_follower")
    parser.add_argument("--save-track", action='store_true', help="Save the track to a file.")
    parser.add_argument("--reverse", action='store_true', help="Reverse the track.")
    parser.add_argument("--service-config", type=Path, help="Path to the service config file.")
    args = parser.parse_args()

    # Create the asyncio event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
