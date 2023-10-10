"""Example using the controller service to drive a 1 meter square."""
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

from farm_ng.control.control_pb2 import ControllerState
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng.filter.filter_pb2 import FilterTrack
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64
from google.protobuf.empty_pb2 import Empty
from google.protobuf.wrappers_pb2 import StringValue


async def get_pose(service_config: EventServiceConfig) -> Pose3F64:
    """Get the current pose of the robot in the world frame, from the controller service.

    Args:
        service_config (EventServiceConfig): The controller service config.
    """
    reply = await EventClient(service_config).request_reply("/get_pose", Empty(), decode=True)
    print(f"Current pose:\n{reply}")
    return Pose3F64.from_proto(reply)


async def set_track(service_config: EventServiceConfig, filter_track: FilterTrack) -> None:
    """Set the track of the controller.

    WARNING: This API will change in the future.
    The controller service currently expects a FilterTrack proto message,
    but this will change in the future to a more general message type.

    Args:
        service_config (EventServiceConfig): The controller service config.
        filter_track (FilterTrack): The track for the controller to follow.
    """
    print(f"Setting track:\n{filter_track}")
    await EventClient(service_config).request_reply("/set_track", filter_track)


async def follow_track(service_config: EventServiceConfig) -> None:
    """Follow the track.

    Args:
        service_config (EventServiceConfig): The controller service config.
    """
    print("Following track...")
    await EventClient(service_config).request_reply("/follow_track", StringValue(value="my_custom_track"))


async def build_square(service_config: EventServiceConfig, side_length: float, clockwise: bool) -> FilterTrack:
    """Build a square track, from the current pose of the robot.

    Args:
        service_config (EventServiceConfig): The controller service config.
        side_length (float): The side length of the square.
        clockwise (bool): True will drive the square clockwise (right hand turns).
                        False is counter-clockwise (left hand turns).
    """

    # Query the controller for the current pose of the robot in the world frame
    world_pose_robot: Pose3F64 = await get_pose(service_config)

    # Create a container to store the track waypoints
    track_waypoints: list[Pose3F64] = []

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

    # # Add third side and turn
    track_waypoints.extend(create_straight_segment(track_waypoints[-1], "goal5", side_length))
    track_waypoints.extend(create_turn_segment(track_waypoints[-1], "goal6", angle))

    # # Add fourth side and turn
    track_waypoints.extend(create_straight_segment(track_waypoints[-1], "goal7", side_length))
    track_waypoints.extend(create_turn_segment(track_waypoints[-1], "goal8", angle))

    # Return the list of waypoints as a FilterTrack proto message
    # This is the format currently expected by the controller service
    return format_track(track_waypoints)


def create_straight_segment(
    previous_pose: Pose3F64, next_frame_b: str, distance: float, spacing: float = 0.1
) -> list[Pose3F64]:
    """Compute a straight segment of a square.

    Args:
        previous_pose (Pose3F64): The previous pose.
        next_frame_b (str): The name of the child frame of the next pose.
        distance (float): The side length of the square.
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
        segment_distance: float = min(remaining_distance, spacing)

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
        segment_angle: float = min(remaining_angle, spacing)

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


def format_track(track_waypoints: list[Pose3F64]) -> FilterTrack:
    """Pack the track waypoints into a FilterTrack proto message.

    WARNING: This API will change in the future.
    The controller service currently expects a FilterTrack proto message,
    but this will change in the future to a more general message type.

    Args:
        track_waypoints (list[Pose3F64]): The track waypoints.
    """
    return FilterTrack(states=[FilterState(pose=pose.to_proto()) for pose in track_waypoints], name="my_custom_track")


async def main(service_config_path: Path, side_length: float) -> None:
    """Run the controller square example. The robot will drive a square, turning left at each corner.

    Args:
        service_config_path (Path): The path to the controller service config.
    """

    # Extract the controller service config from the JSON file
    service_config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    # Build the track and package in a FilterTrack proto message
    filter_track: FilterTrack = await build_square(service_config, side_length)

    # Send the track to the controller
    await set_track(service_config, filter_track)

    # Follow the track
    await follow_track(service_config)


async def stream_controller_state(service_config_path: Path) -> None:
    """Stream the controller state.

    Args:
        service_config_path (Path): The path to the controller service config.
    """

    # Brief wait to allow the controller to start (not necessary in practice)
    await asyncio.sleep(1)
    print("Streaming controller state...")

    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    message: ControllerState
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        print("###################")
        print(message)


async def run(args) -> None:
    tasks: list[asyncio.Task] = [
        asyncio.create_task(main(args.service_config, args.side_length)),
        asyncio.create_task(stream_controller_state(args.service_config)),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-controller-square")
    parser.add_argument("--service-config", type=Path, required=True, help="The controller service config.")
    parser.add_argument("--side-length", type=float, default=1.0, help="The side length of the square.")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
