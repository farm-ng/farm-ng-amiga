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
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng.track.track_pb2 import Track
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from google.protobuf.empty_pb2 import Empty
from track_planner import TrackBuilder

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
    arrow_interval = 20  # Adjust this to change the frequency of arrows
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
            plt.quiver(x[i], y[i], U[i], V[i], angles='xy', scale_units='xy', scale=3.5, color='blue')

    plt.plot(x[0], y[0], marker="o", markersize=5, color='red')
    plt.axis("equal")
    legend_elements = [
        plt.Line2D([0], [0], color='orange', lw=2, label='Track'),
        plt.Line2D([0], [0], color='blue', lw=2, label='Heading'),
        plt.scatter([], [], color='red', marker='o', s=30, label='Start'),
    ]
    plt.legend(handles=legend_elements)
    plt.show()


async def create_start_pose(client: EventClient | None = None, timeout: float = 0.5) -> Pose3F64:
    """Create a start pose for the track.

    Args:
        client: A EventClient for the required service (filter)
    Returns:
        The start pose (Pose3F64)
    """
    print("Creating start pose...")

    zero_tangent = np.zeros((6, 1), dtype=np.float64)
    start: Pose3F64 = Pose3F64(
        a_from_b=Isometry3F64(), frame_a="world", frame_b="robot", tangent_of_b_in_a=zero_tangent
    )
    if client is not None:
        try:
            # Get the current state of the filter
            state: FilterState = await asyncio.wait_for(
                client.request_reply("/get_state", Empty(), decode=True), timeout=timeout
            )
            start = Pose3F64.from_proto(state.pose)
        except asyncio.TimeoutError:
            print("Timeout while getting filter state. Using default start pose.")
        except Exception as e:
            print(f"Error getting filter state: {e}. Using default start pose.")

    return start


async def build_track(reverse: bool, client: EventClient | None = None, save_track: Path | None = None) -> Track:
    """Builds a custom track for the Amiga to follow.

    Args:
        reverse: Whether or not to reverse the track
        client: A EventClient for the required service (filter)
        save_track: The path to save the track to
    Returns:
        The track
    """
    print("Building track...")

    row_spacing: float = 48 * 0.0254  # 48 inches in meters
    row_length: float = 32 * 12 * 0.0254  # 32 feet in meters

    # Path: Start at the beginning row 2, go up on 2, down on row 4, up on row 1, down on row 3, up on row 1,
    # down on row 4, and finish lining up on row 2
    # Assumption: At run time, the robot is positioned at the beginning of row 2, facing the end of row 2.

    start: Pose3F64 = await create_start_pose(client)

    track_builder = TrackBuilder(start=start)

    # Drive forward 32 ft (up row 2)
    track_builder.create_straight_segment(next_frame_b="goal1", distance=row_length, spacing=0.1)

    # Maneuver at the end of row: skip one row (96 inches) - (go from 2 to 4)
    track_builder.create_arc_segment(next_frame_b="goal2", radius=row_spacing, angle=radians(180), spacing=0.1)

    # Drive forward 32 ft (down 4)
    track_builder.create_straight_segment(next_frame_b="goal3", distance=row_length, spacing=0.1)

    # # Maneuver at the end of row: skip two rows (144 inches) - (go from 4 to 1)
    # track_builder.create_arc_segment(next_frame_b="goal4", radius=1.5 * row_spacing, angle=radians(180), spacing=0.1)

    # # Drive forward 32 ft (up 1)
    # track_builder.create_straight_segment(next_frame_b="goal5", distance=row_length, spacing=0.1)

    # # Maneuver at the end of row: skip one row (96 inches) - (go from 1 to 3)
    # track_builder.create_arc_segment(next_frame_b="goal6", radius=row_spacing, angle=radians(180), spacing=0.1)

    # # Drive forward 32 ft (down 3)
    # track_builder.create_straight_segment(next_frame_b="goal7", distance=row_length, spacing=0.1)

    # # Maneuver at the end of row: skip one row (96 inches) - (go from 3 to 1)
    # track_builder.create_arc_segment(next_frame_b="goal8", radius=row_spacing, angle=radians(180), spacing=0.1)

    # # Drive forward 32 ft (up 1)
    # track_builder.create_straight_segment(next_frame_b="goal9", distance=row_length, spacing=0.1)

    # # Maneuver at the end of row: skip two rows (144 inches) - (go from 1 to 4)
    # track_builder.create_arc_segment(next_frame_b="goal10", radius=1.5 * row_spacing, angle=radians(180), spacing=0.1)

    # # Drive forward 32 ft (down 4)
    # track_builder.create_straight_segment(next_frame_b="goal11", distance=row_length, spacing=0.1)

    # # Maneuver at the end of row: skip one row (96 inches) - (go from 4 to 2 - slightly before the start)
    # track_builder.create_arc_segment(next_frame_b="goal12", radius=row_spacing, angle=radians(175), spacing=0.1)

    if reverse:
        track_builder.reverse_track()

    # Print the number of waypoints in the track
    print(f" Track created with {len(track_builder.track_waypoints)} waypoints")

    # Save the track to a file
    if save_track is not None:
        track_builder.save_track(save_track)

    # Plot the track
    waypoints = track_builder.unpack_track()
    plot_track(waypoints)
    return track_builder.track


async def run(args) -> None:
    # Create flag for saving track
    save_track: bool = args.save_track
    reverse: bool = args.reverse

    client: EventClient | None = None

    if args.service_config is not None:
        client = EventClient(proto_from_json_file(args.service_config, EventServiceConfig()))
        if client is None:
            raise RuntimeError(f"No filter service config in {args.service_config}")
        if client.config.name != "filter":
            raise RuntimeError(f"Expected filter service in {args.service_config}, got {client.config.name}")

    # Start the asyncio tasks
    tasks: list[asyncio.Task] = [asyncio.create_task(build_track(reverse, client, save_track))]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-track_follower")
    parser.add_argument("--save-track", type=Path, help="Save the track to a file.")
    parser.add_argument("--reverse", action='store_true', help="Reverse the track.")
    parser.add_argument("--service-config", type=Path, help="Path to the service config file.")
    args = parser.parse_args()

    # Create the asyncio event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
