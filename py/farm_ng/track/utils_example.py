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
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.uri_pb2 import Uri
from farm_ng.track.track_pb2 import Track
from farm_ng.track.track_pb2 import TrackFollowerState
from farm_ng.track.track_pb2 import TrackFollowRequest
from farm_ng.track.utils import TrackBuilder
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64
from google.protobuf.empty_pb2 import Empty

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


async def set_track(clients: dict[str, EventClient], track: Track) -> None:
    """Set the track of the track_follower.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
        track (Track): The track for the track_follower to follow.
    """
    print(f"Setting track:\n{track}")
    await clients["track_follower"].request_reply("/set_track", TrackFollowRequest(track=track))


async def start(clients: dict[str, EventClient]) -> None:
    """Request to start following the track.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
    """
    print("Sending request to start following the track...")
    await clients["track_follower"].request_reply("/start", Empty())


async def build_track(
    clients: dict[str, EventClient], side_length: float, angle: float, clockwise: bool = False
) -> Track:
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

    # Set the angle of the turns, based on indicated direction
    if clockwise:
        angle = -angle

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


async def start_track(clients: dict[str, EventClient], side_length: float, clockwise: bool) -> None:
    """Build the track, send it to the track_follower, and start following the track.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
        side_length (float): The side length of the square.
        clockwise (bool): True will drive the square clockwise (right hand turns).
                        False is counter-clockwise (left hand turns).
    """

    await build_track(clients, side_length, 180, clockwise=clockwise)

    # Send the track to the track_follower
    # await set_track(clients, track)

    # Start following the track
    # await start(clients)


async def stream_track_state(clients: dict[str, EventClient]) -> None:
    """Stream the track_follower state.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
    """

    # Brief wait to allow you to see the track sent to the track_follower
    # Note that this is not necessary in practice
    await asyncio.sleep(1.0)

    # Subscribe to the track_follower state and print each
    message: TrackFollowerState
    async for _, message in clients["track_follower"].subscribe(SubscribeRequest(uri=Uri(path="/state"))):
        print("-" * 50)
        print(message)


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
    tasks: list[asyncio.Task] = [
        asyncio.create_task(start_track(clients, args.side_length, args.clockwise)),
        asyncio.create_task(stream_track_state(clients)),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-track_follower-square")
    parser.add_argument("--service-config", type=Path, required=True, help="The service config.")
    parser.add_argument("--side-length", type=float, default=2.0, help="The side length of the square.")
    parser.add_argument(
        "--clockwise",
        action="store_true",
        help="Set to drive the square clockwise (right hand turns). Default is counter-clockwise (left hand turns).",
    )
    args = parser.parse_args()

    # Create the asyncio event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
