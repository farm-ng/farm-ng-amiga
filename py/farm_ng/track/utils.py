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
from math import copysign
from pathlib import Path

import numpy as np
from farm_ng.core.event_client import EventClient
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.events_file_writer import proto_to_json_file
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng.filter.filter_pb2 import FilterTrack
from farm_ng.track.track_pb2 import Track
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64
from google.protobuf.empty_pb2 import Empty

# WARNING: These methods are a temporary convenience and will be removed
# once the use of FilterTrack protos has been fully phased out.


def filter_track_to_track(filter_track: FilterTrack) -> Track:
    """Converts a FilterTrack proto to a generic Track proto.

    Args:
        filter_track: A FilterTrack proto.
    Returns: A Track proto.
    """
    if not isinstance(filter_track, FilterTrack):
        raise TypeError(f"Expected FilterTrack, got {type(filter_track)}")
    return Track(waypoints=[state.pose for state in filter_track.states])


def update_filter_track(track_path: Path) -> None:
    """Updates a .json file with a FilterTrack proto to a generic Track proto.

    Args:
        track_path: The path to the .json file.
    """
    filter_track: FilterTrack = proto_from_json_file(track_path, FilterTrack())
    track: Track = filter_track_to_track(filter_track)
    proto_to_json_file(track_path, track)


class TrackBuilder:
    """A class for building tracks."""

    def __init__(self, clients) -> None:
        self.clients: dict[str, EventClient] = clients
        self._start: Pose3F64
        self.track_waypoints: list[Pose3F64] = []
        self._segment_indices: list[int] = [0]
        self._loaded: bool = False
        self._track: Track | None = None

    @classmethod
    async def create(cls, clients, pose: Pose3F64 = None, timeout=3.0):
        """Create a TrackBuilder instance with an initial default pose."""
        self = cls(clients)

        # Initialize with a default pose

        if pose is not None:
            self._start = pose

        else:
            zero_tangent = np.zeros((6, 1), dtype=np.float64)
            self._start = Pose3F64(
                a_from_b=Isometry3F64(), frame_a="world", frame_b="robot", tangent_of_b_in_a=zero_tangent
            )

            # Attempt to get the actual pose with a timeout
            try:
                updated_start = await asyncio.wait_for(self.get_pose(), timeout)
                self._start = updated_start
                print(f"Start pose:\n{self._start.a_from_b.translation}")
            except asyncio.TimeoutError:
                print("Timeout occurred when trying to get pose from filter, using default pose")

        # Initialize the track_waypoints with the start pose
        self.track_waypoints = [self._start]
        return self

    @property
    def track(self) -> Track:
        """Pack the track waypoints into a Track proto message."""
        return Track(waypoints=[pose.to_proto() for pose in self.track_waypoints])

    @track.setter
    def track(self, loaded_track: Track) -> None:
        """Unpack a Track proto message into the track waypoints."""
        self._track = loaded_track
        self.track_waypoints = [Pose3F64.from_proto(pose) for pose in self.track.waypoints]
        self._loaded = True

    async def get_pose(self) -> Pose3F64:
        """Get the current pose of the robot in the world frame, from the filter service.

        Args: None
        Returns:
            Pose3F64: The current pose of the robot in the world frame.
        """
        # We use the FilterState as the best source of the current pose of the robot
        state: FilterState = await self.clients["filter"].request_reply("/get_state", Empty(), decode=True)
        return Pose3F64.from_proto(state.pose)

    def create_straight_segment(self, next_frame_b: str, distance: float, spacing: float = 0.1) -> None:
        """Compute a straight segment.

        Args:
            next_frame_b (str): The name of the child frame of the next pose.
            distance (float): The length of the segment, in meters.
            spacing (float): The spacing between waypoints, in meters.

        Returns:
            None: The segment generated is appended to the current list of waypoints.
        """
        # Create a container to store the track segment waypoints
        segment_poses: list[Pose3F64] = [self.track_waypoints[-1]]

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
        self.track_waypoints.extend(segment_poses)
        self._segment_indices.append(len(self.track_waypoints))
        self._loaded = False

    def create_ab_segment(self, next_frame_b: str, final_pose: Pose3F64, spacing: float = 0.1) -> None:
        """Compute an AB line segment.
        Args:
            next_frame_b (str): The name of the child frame of the next pose.
            initial_pose (Pose3F64): The initial pose of the segment.
            final_pose (Pose3F64): The final pose of the segment.
            spacing (float): The spacing between waypoints, in meters.

        Returns:
            None: The segment generated is appended to the current list of waypoints.
        """

        # Calculate distance between initial and final pose
        initial_pose: Pose3F64 = self.track_waypoints[-1]
        distance: float = np.linalg.norm(initial_pose.a_from_b.translation - final_pose.a_from_b.translation)

        # Calculate number of waypoints in the segment
        num_segments = max(int(distance / spacing), 1)
        delta_distance = distance / num_segments

        # Distance increment per segment

        # Create a container to store the track segment waypoints
        segment_poses: list[Pose3F64] = [self.track_waypoints[-1]]

        for i in range(1, num_segments + 1):
            # Calculate the pose for the current segment
            fraction_segment: Pose3F64 = Pose3F64(
                a_from_b=Isometry3F64([delta_distance, 0, 0], Rotation3F64.Rz(0)),
                frame_a=segment_poses[-1].frame_b,
                frame_b=f"{next_frame_b}_{i - 1}",
            )
            segment_poses.append(segment_poses[-1] * fraction_segment)

        # Rename the last pose to the desired name
        segment_poses[-1].frame_b = next_frame_b
        self.track_waypoints.extend(segment_poses)
        self._segment_indices.append(len(self.track_waypoints))
        self._loaded = False

    def create_turn_segment(self, next_frame_b: str, angle: float, spacing: float = 0.1) -> None:
        """Compute a turn (in place) segment.

        Args:
            next_frame_b (str): The name of the child frame of the next pose.
            angle (float): The angle to turn, in radians (+ left, - right).
            spacing (float): The spacing between waypoints, in radians.
        Returns:
            None: The segment generated is appended to the current list of waypoints.
        """
        # Create a container to store the track segment waypoints
        segment_poses: list[Pose3F64] = [self.track_waypoints[-1]]

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
        self.track_waypoints.extend(segment_poses)
        self._segment_indices.append(len(self.track_waypoints))
        self._loaded = False

    def create_arc_segment(self, next_frame_b: str, radius: float, angle: float, spacing: float = 0.1) -> None:
        """Compute an arc segment.

        Args:
            next_frame_b (str): The name of the child frame of the next pose.
            radius (float): The radius of the arc.
            angle (float): The angle to turn, in radians (+ left, - right).
            spacing (float): The spacing between waypoints, in meters.

        Returns:
            None: The segment generated is appended to the current list of waypoints.
        """
        # Calculate the total arc length
        arc_length = abs(angle * radius)

        # Determine the number of segments, ensuring at least one segment
        num_segments = max(int(arc_length / spacing), 1)

        # Angle increment per segment
        delta_angle = angle / num_segments

        # Distance increment per segment
        delta_distance = arc_length / num_segments

        # Create a container to store the track segment waypoints
        segment_poses: list[Pose3F64] = [self.track_waypoints[-1]]

        for i in range(1, num_segments + 1):
            # Calculate the pose for the current segment
            turn_segment: Pose3F64 = Pose3F64(
                a_from_b=Isometry3F64([delta_distance, 0, 0], Rotation3F64.Rz(delta_angle)),
                frame_a=segment_poses[-1].frame_b,
                frame_b=f"{next_frame_b}_{i - 1}",
            )
            segment_poses.append(segment_poses[-1] * turn_segment)

        # Rename the last pose to the desired name
        segment_poses[-1].frame_b = next_frame_b
        self.track_waypoints.extend(segment_poses)
        self._segment_indices.append(len(self.track_waypoints))
        self._loaded = False

    def pop_last_segment(self) -> None:
        """Remove the last (appended) segment from the track."""

        if self._loaded:
            print("Cannot pop segment from a loaded track without inserting new segments first.")
            return

        if len(self._segment_indices) > 1:  # Ensure there is a segment to pop
            last_segment_start = self._segment_indices[-2]  # Get the start of the last segment
            # Remove the waypoints from the last segment
            self.track_waypoints = self.track_waypoints[:last_segment_start]
            # Remove the last segment index
            self._segment_indices.pop()
        else:
            print("No segment to pop.")

    def unpack_track(self) -> tuple[list[float], list[float], list[float]]:
        """Unpack x and y coordinates and heading from the waypoints for plotting.

        Args: None
        Returns:
            tuple[list[float], list[float], list[float]]: The x, y, and heading coordinates of the track waypoints.
        """

        x: list[float] = []
        y: list[float] = []
        heading: list[float] = []
        for pose in self.track_waypoints:
            x.append(pose.a_from_b.translation[0])
            y.append(pose.a_from_b.translation[1])
            heading.append(pose.a_from_b.rotation.log()[-1])
        return (x, y, heading)

    def save_track(self, path: Path) -> None:
        """Save the track to a json file.

        Args:
            path (Path): The path of the file to save.
        """
        if self.track:
            proto_to_json_file(path, self.track)
            print(f"Track saved to {path}")
        else:
            print("No track to save.")

    def load_track(self, path: Path) -> None:
        """Import a track from a json file.

        Args:
            path (Path): The path of the file to import.
        """
        loaded_track = proto_from_json_file(path, Track())
        self.track = loaded_track
