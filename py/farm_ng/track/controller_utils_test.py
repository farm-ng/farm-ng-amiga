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
from math import sqrt
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

# from controller_utils import TrackBuilder

matplotlib.use("TkAgg")  # Set the backend to Agg for non-GUI environments


def yaw_to_quaternion(yaw_degrees):
    """Convert yaw angle to radians
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


async def build_square(clients: dict[str, EventClient], side_length: float, clockwise: bool) -> Track:
    """Build a square track, from the current pose of the robot.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
        side_length (float): The side length of the square, in meters.
        clockwise (bool): True will drive the square clockwise (right hand turns).
                        False is counter-clockwise (left hand turns).
    Returns:
        Track: The track for the track_follower to follow.
    """
    print("Building square track...")
    track_builder = await TrackBuilder.create(clients=clients)

    # Set the angle of the turns, based on indicated direction
    angle: float = -90 if clockwise else 90

    # Drive forward 1 meter (first side of the square)
    track_builder.create_straight_segment("goal1", side_length)

    # Turn left 90 degrees (first turn)
    track_builder.create_turn_segment("goal2", radians(angle))

    # Add second side and turn
    track_builder.create_straight_segment("goal3", side_length)
    track_builder.create_turn_segment("goal4", radians(angle))

    # Add third side and turn
    track_builder.create_straight_segment("goal5", side_length)
    track_builder.create_turn_segment("goal6", radians(angle))

    # Add fourth side and turn
    track_builder.create_straight_segment("goal7", side_length)
    track_builder.create_turn_segment("goal8", radians(angle))

    # Return the list of waypoints as a Track proto message
    track_builder.format_track()
    print(len(track_builder.track_waypoints))

    # Remove the last two segments (turn and straight segment - for testing purposes)
    track_builder.pop_last_segment()
    track_builder.pop_last_segment()
    print(len(track_builder.track_waypoints))

    # Plot the track
    waypoints = track_builder.unpack_track()
    x = waypoints[0]
    y = waypoints[1]
    plt.plot(x, y)
    plt.savefig("build_square.png")

    return track_builder.track


async def build_pi_turn(
    clients: dict[str, EventClient], side_length: float, angle: float, clockwise: bool = False
) -> Track:
    """Build a track with a U-turn, from the current pose of the robot.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
        side_length (float): The side length of the square, in meters.
        clockwise (bool): True will drive the square clockwise (right hand turns).
                        False is counter-clockwise (left hand turns).
    Returns:
        Track: The track for the track_follower to follow.
    """
    print("Building pi-turn track...")

    # Set the initial pose of the robot
    # Set the initial heading of the robot
    # unit_quaternion = np.array([0.0, 0.0, 0.0, 1.0])  # Start at 0 degrees
    unit_quaternion = np.array([0.0, 0.0, sqrt(0.5), sqrt(0.5)])  # Start at 90 degrees
    # unit_quaternion = np.array([0.0, 0.0, sqrt(1 - 0.924**2), 0.924])  #  Start at 45 degrees
    rotation = Rotation3F64(unit_quaternion.reshape((4, 1)))
    # Set the initial position of the robot
    a_from_b = Isometry3F64(rotation=rotation, translation=[7.0, 10.0, 0.0])

    initial_pose = Pose3F64(
        a_from_b=a_from_b, frame_a="world", frame_b="robot", tangent_of_b_in_a=np.zeros((6, 1), dtype=np.float64)
    )

    track_builder = await TrackBuilder.create(clients=clients, pose=initial_pose)

    # Set the angle of the turns, based on indicated direction
    if clockwise:
        angle = -angle

    # Drive forward 1 meter (first side of the square)
    track_builder.create_straight_segment("goal1", 10)

    # Turn left 90 degrees (first turn)
    track_builder.create_arc_segment("goal2", radius=48 * 0.0254, angle=radians(angle), spacing=0.1)

    # Add second side and turn
    track_builder.create_straight_segment("goal3", 10)

    # Add third side and turn
    track_builder.create_arc_segment("goal3", radius=48 * 0.0254, angle=radians(angle), spacing=0.1)

    print(len(track_builder.track_waypoints))

    # Plot the track
    waypoints = track_builder.unpack_track()
    x = waypoints[0]
    y = waypoints[1]
    plt.plot(x, y)
    plt.axis("equal")
    plt.savefig("pi_turn.png")
    plt.show()

    track_builder.format_track()
    script_path = Path(__file__)  # Current script's path
    parent_directory = script_path.parent
    file_path = parent_directory / "pi_turn.json"

    track_builder.save_track(file_path)

    return track_builder.track


async def build_test_track(
    clients: dict[str, EventClient], side_length: float, angle: float, clockwise: bool = False
) -> Track:
    """Build a custom track for assessing the performance of the autoplot app.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
        side_length (float): The side length of the square, in meters.
        clockwise (bool): True will drive the square clockwise (right hand turns).
                        False is counter-clockwise (left hand turns).
    Returns:
        Track: The track for the track_follower to follow.
    """
    print("Building autoplot test track...")

    # Set the initial pose of the robot
    unit_quaternion = yaw_to_quaternion(-135)  # Start at 90 degrees (facing East)
    rotation = Rotation3F64(unit_quaternion.reshape((4, 1)))
    a_from_b = Isometry3F64(rotation=rotation, translation=[7.0, 10.0, 0.0])

    initial_pose = Pose3F64(
        a_from_b=a_from_b, frame_a="world", frame_b="robot", tangent_of_b_in_a=np.zeros((6, 1), dtype=np.float64)
    )

    track_builder = await TrackBuilder.create(clients=clients, pose=initial_pose)

    # Set the angle of the turns, based on indicated direction
    if clockwise:
        angle = -angle

    # Drive forward 2 meter (first side of the square)
    track_builder.create_straight_segment("goal1", 2)

    # Turn in place 90 degrees (first turn)
    track_builder.create_turn_segment("goal2", radians(90))

    # Drive forward 2 meter (second side of the square)
    track_builder.create_straight_segment("goal3", 2)

    # Turn in place -45 degrees (second turn)
    track_builder.create_turn_segment("goal4", radians(-45))

    # Drive forward 2 meter (third side of the square)
    track_builder.create_straight_segment("goal5", 2)

    # Turn in place -90 degrees (third turn)
    track_builder.create_turn_segment("goal6", radians(-90))

    # Drive forward 2 meter (fourth side of the square)
    track_builder.create_straight_segment("goal7", 2)

    # S curve
    track_builder.create_arc_segment("goal8", radius=40 * 0.0254, angle=radians(180), spacing=0.1)
    track_builder.create_straight_segment("goal9", 2)
    track_builder.create_arc_segment("goal10", radius=60 * 0.0254, angle=radians(-180), spacing=0.1)
    track_builder.create_straight_segment("goal11", 2.0)
    track_builder.create_arc_segment("goal12", radius=48 * 0.0254, angle=radians(-90), spacing=0.1)
    track_builder.create_straight_segment("goal13", 9)

    # Turn in place 90 degrees (fourth turn)
    track_builder.create_turn_segment("goal14", radians(-90))

    # Drive back to origin
    track_builder.create_straight_segment("goal15", 3.2)

    # Get closer to original orientation
    track_builder.create_turn_segment("goal16", radians(-125))
    # track_builder.create_straight_segment("goal17", 2.5) # uncomment for visualization purposes

    print(len(track_builder.track_waypoints))

    # Plot the track
    waypoints = track_builder.unpack_track()
    x = waypoints[0]
    y = waypoints[1]
    plt.plot(x, y)
    plt.axis("equal")
    plt.savefig("autoplot.png")
    plt.show()

    track_builder.format_track()
    script_path = Path(__file__)  # Current script's path
    parent_directory = script_path.parent
    file_path = parent_directory / "autoplot_test.json"

    track_builder.save_track(file_path)

    return track_builder.track


async def pose_segment(clients: dict[str, EventClient]) -> Track:
    """Build a track with a U-turn, from the current pose of the robot.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
        side_length (float): The side length of the square, in meters.
        clockwise (bool): True will drive the square clockwise (right hand turns).
                        False is counter-clockwise (left hand turns).
    Returns:
        Track: The track for the track_follower to follow.
    """
    print("Building pose_segment track...")

    # Set the initial pose of the robot
    xi = 6.7306
    yi = 1.58
    xf = 5.296
    yf = 26.2896
    dx = xf - xi
    dy = yf - yi
    dl = sqrt(dx**2 + dy**2)
    heading = np.degrees(np.arccos(dx / dl))
    print(f"Heading: {heading}")
    quaternion = yaw_to_quaternion(heading)
    rotation = Rotation3F64(quaternion.reshape((4, 1)))
    a_from_b_initial = Isometry3F64(rotation=rotation, translation=[xi, yi, 0.0])
    a_from_b_final = Isometry3F64(rotation=rotation, translation=[xf, yf, 0.0])

    initial_pose = Pose3F64(
        a_from_b=a_from_b_initial,
        frame_a="world",
        frame_b="robot",
        tangent_of_b_in_a=np.zeros((6, 1), dtype=np.float64),
    )

    final_pose = Pose3F64(
        a_from_b=a_from_b_final, frame_a="world", frame_b="robot", tangent_of_b_in_a=np.zeros((6, 1), dtype=np.float64)
    )

    track_builder = await TrackBuilder.create(clients=clients, pose=initial_pose)

    # Drive forward 1 meter (first side of the square)
    track_builder.create_ab_segment("goal1", initial_pose, final_pose)

    print(len(track_builder.track_waypoints))

    # Plot the track
    waypoints = track_builder.unpack_track()
    x = waypoints[0]
    y = waypoints[1]
    plt.plot(x, y)
    plt.axis("equal")
    plt.savefig("AB.png")
    plt.show()

    track_builder.format_track()
    script_path = Path(__file__)  # Current script's path
    parent_directory = script_path.parent
    file_path = parent_directory / "AB.json"

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

    # Build the track and package in a Track proto message
    # await build_square(clients, side_length, clockwise)
    await build_pi_turn(clients, side_length, 180, clockwise=clockwise)
    # await build_test_track(clients, side_length, 180, clockwise=clockwise)
    # await pose_segment(clients)

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
