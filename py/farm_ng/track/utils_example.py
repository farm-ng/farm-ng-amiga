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
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64

matplotlib.use("TkAgg")  # Set the backend to Agg for non-GUI environments

# Create a couple of helper functions to easily create poses and quaternions


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


async def build_track(clients: dict[str, EventClient]) -> Track:
    """Build a custom track. Here, we will use all the functions in the TrackBuilder class for educational
    purposes.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
        side_length (float): The side length of the square, in meters.
        clockwise (bool): True will drive the square clockwise (right hand turns).
                        False is counter-clockwise (left hand turns).
    Returns:
        Track: The track for the track_follower to follow.
    """
    print("Building track...")

    # Set the initial pose of the robot
    initial_pose = create_pose(x=7.0, y=10.0, heading=-135)

    # Set the second pose of the robot to demonstrate how to create an ab_segment
    second_pose = create_pose(x=9.0, y=10.0, heading=-135)

    # Start the track builder
    track_builder = await TrackBuilder.create(clients=clients, pose=initial_pose)

    # Drive forward from the initial pose to the second pose
    track_builder.create_ab_segment("goal1", second_pose)

    # Turn in place 90 degrees
    track_builder.create_turn_segment("goal2", radians(90))

    # Drive forward 3 meters
    track_builder.create_straight_segment("goal3", 3)

    # Smooth u-turn (radius = 60 inches)
    track_builder.create_arc_segment("goal8", radius=60 * 0.0254, angle=radians(180), spacing=0.1)

    # Drive forward 3.1 meters
    track_builder.create_straight_segment("goal9", 3.1)

    # Turn in place 90 degrees
    track_builder.create_turn_segment("goal4", radians(90))

    # Drive forward 0.85 meters to "close" the loop
    track_builder.create_straight_segment("goal5", 0.85)

    # Print the number of waypoints in the track
    print(len(track_builder.track_waypoints))

    # Plot the track
    waypoints = track_builder.unpack_track()
    x = waypoints[0]
    y = waypoints[1]
    plt.plot(x, y)
    plt.axis("equal")
    plt.savefig("my_track.png")  # Save the image of the track for visualization purposes
    plt.show()

    # Save the track to a file
    track_builder.format_track()
    script_path = Path(__file__)  # Current script's path
    parent_directory = script_path.parent
    file_path = parent_directory / "my_track.json"

    track_builder.save_track(file_path)

    return track_builder.track


async def run(args) -> None:
    # Create a dictionary of EventClients to the services required by this example
    clients: dict[str, EventClient] = {}
    expected_configs = ["track_follower", "filter"]
    config_list = proto_from_json_file(args.service_config, EventServiceConfigList())
    for config in config_list.configs:
        if config.name in expected_configs:
            clients[config.name] = EventClient(config)

    # Confirm that EventClients were created for all required services
    for config in expected_configs:
        if config not in clients:
            raise RuntimeError(f"No {config} service config in {args.service_config}")

    # Start the asyncio tasks
    tasks: list[asyncio.Task] = [asyncio.create_task(build_track(clients))]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-track_follower-square")
    parser.add_argument("--service-config", type=Path, required=True, help="The service config.")
    args = parser.parse_args()

    # Create the asyncio event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
