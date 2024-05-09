"""Example using the track_follower service to drive a square."""
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
from math import copysign
from math import radians
from pathlib import Path

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.uri_pb2 import Uri
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng.track.track_pb2 import Track
from farm_ng.track.track_pb2 import TrackFollowerState
from farm_ng.track.track_pb2 import TrackFollowRequest
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64
from google.protobuf.empty_pb2 import Empty


async def get_pose(clients: dict[str, EventClient]) -> Pose3F64:
    """Get the current pose of the robot in the world frame, from the filter service.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
    """
    # We use the FilterState as the best source of the current pose of the robot
    state: FilterState = await clients["filter"].request_reply("/get_state", Empty(), decode=True)
    print(f"Current filter state:\n{state}")
    return Pose3F64.from_proto(state.pose)


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

    # Query the state estimation filter for the current pose of the robot in the world frame
    world_pose_robot: Pose3F64 = await get_pose(clients)

    # Create a container to store the track waypoints
    track_waypoints: list[Pose3F64] = []

    # Set the angle of the turns, based on indicated direction
    angle: float = radians(-90) if clockwise else radians(90)

    # Add the first goal at the current pose of the robot
    world_pose_goal0: Pose3F64 = world_pose_robot * Pose3F64(a_from_b=Isometry3F64(), frame_a="robot", frame_b="goal0")
    track_waypoints.append(world_pose_goal0)

    # Drive forward 1 meter (first side of the square)
    track_waypoints.extend(create_straight_segment(track_waypoints[-1], "goal1", side_length))

    # Turn left 90 degrees (first turn)
    track_waypoints.extend(create_turn_segment(track_waypoints[-1], "goal2", angle))

    # Add second side and turn
    track_waypoints.extend(create_straight_segment(track_waypoints[-1], "goal3", side_length))
    track_waypoints.extend(create_turn_segment(track_waypoints[-1], "goal4", angle))

    # Add third side and turn
    track_waypoints.extend(create_straight_segment(track_waypoints[-1], "goal5", side_length))
    track_waypoints.extend(create_turn_segment(track_waypoints[-1], "goal6", angle))

    # Add fourth side and turn
    track_waypoints.extend(create_straight_segment(track_waypoints[-1], "goal7", side_length))
    track_waypoints.extend(create_turn_segment(track_waypoints[-1], "goal8", angle))

    # Return the list of waypoints as a Track proto message
    return format_track(track_waypoints)


def create_straight_segment(
    previous_pose: Pose3F64, next_frame_b: str, distance: float, spacing: float = 0.1
) -> list[Pose3F64]:
    """Compute a straight segment of a square.

    Args:
        previous_pose (Pose3F64): The previous pose.
        next_frame_b (str): The name of the child frame of the next pose.
        distance (float): The side length of the square, in meters.
        spacing (float): The spacing between waypoints, in meters.

    Returns:
        Pose3F64: The poses of the straight segment.
    """
    # Create a container to store the track segment waypoints
    segment_poses: list[Pose3F64] = [previous_pose]

    # For tracking the number of segments and remaining angle
    counter: int = 0
    remaining_distance: float = distance

    while abs(remaining_distance) > 0.01:
        # Compute the distance of the next segment
        segment_distance: float = copysign(min(abs(remaining_distance), spacing), distance)

        # Compute the next pose
        straight_segment: Pose3F64 = Pose3F64(
            a_from_b=Isometry3F64([segment_distance, 0, 0], Rotation3F64.Rz(0)),
            frame_a=segment_poses[-1].frame_b,
            frame_b=f"{next_frame_b}_{counter}",
        )
        segment_poses.append(segment_poses[-1] * straight_segment)

        # Update the counter and remaining angle
        counter += 1
        remaining_distance -= segment_distance

    # Rename the last pose to the desired name
    segment_poses[-1].frame_b = next_frame_b
    return segment_poses


def create_turn_segment(
    previous_pose: Pose3F64, next_frame_b: str, angle: float, spacing: float = 0.1
) -> list[Pose3F64]:
    """Compute a turn segment of a square.

    Args:
        previous_pose (Pose3F64): The previous pose.
        next_frame_b (str): The name of the child frame of the next pose.
        angle (float): The angle to turn, in radians (+ left, - right).
        spacing (float): The spacing between waypoints, in radians.
    Returns:
        list[Pose3F64]: The poses of the turn segment.
    """
    # Create a container to store the track segment waypoints
    segment_poses: list[Pose3F64] = [previous_pose]

    # For tracking the number of segments and remaining angle
    counter: int = 0
    remaining_angle: float = angle

    while abs(remaining_angle) > 0.01:
        # Compute the angle of the next segment
        segment_angle: float = copysign(min(abs(remaining_angle), spacing), angle)

        # Compute the next pose
        turn_segment: Pose3F64 = Pose3F64(
            a_from_b=Isometry3F64.Rz(segment_angle),
            frame_a=segment_poses[-1].frame_b,
            frame_b=f"{next_frame_b}_{counter}",
        )
        segment_poses.append(segment_poses[-1] * turn_segment)

        # Update the counter and remaining angle
        counter += 1
        remaining_angle -= segment_angle

    # Rename the last pose to the desired name
    segment_poses[-1].frame_b = next_frame_b
    return segment_poses


def format_track(track_waypoints: list[Pose3F64]) -> Track:
    """Pack the track waypoints into a Track proto message.

    Args:
        track_waypoints (list[Pose3F64]): The track waypoints.
    """
    return Track(waypoints=[pose.to_proto() for pose in track_waypoints])


async def start_track(clients: dict[str, EventClient], side_length: float, clockwise: bool) -> None:
    """Run the track_follower square example. The robot will drive a square, turning left at each corner.

    Args:
        clients (dict[str, EventClient]): A dictionary of EventClients.
        side_length (float): The side length of the square.
        clockwise (bool): True will drive the square clockwise (right hand turns).
                        False is counter-clockwise (left hand turns).
    """

    # Build the track and package in a Track proto message
    track: Track = await build_square(clients, side_length, clockwise)

    # Send the track to the track_follower
    await set_track(clients, track)

    # Start following the track
    await start(clients)


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
        print("###################")
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
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga track_follower square example.")
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
