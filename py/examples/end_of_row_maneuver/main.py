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
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from end_of_row_maneuver import build_row_end_maneuver
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.track.track_pb2 import Track
from track_planner import TrackBuilder

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


async def build_track(client: EventClient | None = None, save_track: Path | None = None) -> Track:
    """Builds a custom track for the Amiga to follow.

    Args:
        client: A EventClient for the required service (filter)
        save_track: The path to save the track to
    Returns:
        The track
    """
    print("Building track...")

    # NOTE: In this example, we will create a row-end maneuver track.
    # The Amiga will drive forward, turn 90 degrees, drive forward to the next row,
    # turn 90 degrees to align with the next row, and then drive forward again.
    # In this specific example, we will simulate a left turn, use a buffer distance of 2.5 meters
    # and a row spacing of 6.0 meters.

    track: Track = await build_row_end_maneuver(client, buffer_distance=2.5, row_spacing=6.0, direction="left")

    track_builder = TrackBuilder(start=None)
    track_builder.track = track

    # Save the track to a file
    if save_track is not None:
        track_builder.save_track(save_track)

    # Plot the track for visualization
    waypoints = track_builder.unpack_track()
    plot_track(waypoints)
    return track_builder.track


async def run(args) -> None:
    # Create flag for saving track
    save_track: bool = args.save_track

    client: EventClient | None = None

    if args.service_config is not None:
        client = EventClient(proto_from_json_file(args.service_config, EventServiceConfig()))
        if client is None:
            raise RuntimeError(f"No filter service config in {args.service_config}")
        if client.config.name != "filter":
            raise RuntimeError(f"Expected filter service in {args.service_config}, got {client.config.name}")

    # Start the asyncio tasks
    tasks: list[asyncio.Task] = [asyncio.create_task(build_track(client, save_track))]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga path planning example.")
    parser.add_argument("--save-track", type=Path, help="Save the track to a file.")
    parser.add_argument("--service-config", type=Path, help="Path to the service config file.")
    args = parser.parse_args()

    # Create the asyncio event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
