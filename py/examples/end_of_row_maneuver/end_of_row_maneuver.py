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

import asyncio
from math import radians

import numpy as np
from farm_ng.core.event_client import EventClient
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng.track.track_pb2 import Track
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from google.protobuf.empty_pb2 import Empty
from track_planner import TrackBuilder


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


async def build_row_end_maneuver(
    client: EventClient | None = None, forward_turn: float = 2.5, row_spacing: float = 6.0, direction: str = "left"
) -> Track:
    """Builds a custom track for the Amiga to follow.

    Args:
        client: A EventClient for the required service (filter)
    Returns:
        The track
    """

    if client is None:
        raise RuntimeError("EventClient cannot be None")

    print("Building track...")

    current_pose: Pose3F64 = await create_start_pose(client)
    track_builder = TrackBuilder(start=current_pose)
    if direction not in ["left", "right"]:
        raise ValueError("Direction must be 'left' or 'right'")

    turn_sign = 1 if direction == "left" else -1

    # Based on field tests, 'zero-radius turns' are less likely to cause motor overheating issues.
    # For this reason, when transitioning between rows, we will only make zero-radius turns.
    # The goal is to drive forward 2.5 m (buffer distance), turn 90 degrees, drive forward 6 m (row spacing),
    # turn 90 degrees to align with the next row, and then drive forward 2.5 m.

    # Drive forward 2.5 m
    track_builder.create_straight_segment(next_frame_b="goal1", distance=forward_turn, spacing=0.1)

    # Maneuver at the end of row: turn 90 degrees to the left
    track_builder.create_turn_segment(next_frame_b="goal2", angle=radians(90 * turn_sign), spacing=0.1)

    # Drive forward 6 m (row spacing)
    track_builder.create_straight_segment(next_frame_b="goal3", distance=row_spacing, spacing=0.1)

    # Maneuver at the end of row: align with the next row (another 90 degrees to the left)
    track_builder.create_turn_segment(next_frame_b="goal2", angle=radians(90 * turn_sign), spacing=0.1)

    # Drive forward 1m (just for visualization - in reality, we will create an AB segment to the next waypoint)
    track_builder.create_straight_segment(next_frame_b="goal5", distance=forward_turn, spacing=0.1)

    # Print the number of waypoints in the track
    print(f" Track created with {len(track_builder.track_waypoints)} waypoints")

    # Plot the track
    return track_builder.track
