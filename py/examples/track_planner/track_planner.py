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

from pathlib import Path

import numpy as np
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.events_file_writer import proto_to_json_file
from farm_ng.track.track_pb2 import Track
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64


class TrackBuilder:
    """A class for building tracks."""

    def __init__(self, start: Pose3F64 | None = None) -> None:
        """Initialize the TrackBuilder."""
        self._start: Pose3F64 = start if start is not None else Pose3F64()
        self.track_waypoints: list[Pose3F64] = []
        self._segment_indices: list[int] = [0]
        self._loaded: bool = False
        self.track_waypoints = [start]

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

    def _create_segment(self, next_frame_b: str, distance: float, spacing: float, angle: float = 0) -> None:
        """Create a segment with given distance and spacing."""
        # Create a container to store the track segment waypoints
        segment_poses: list[Pose3F64] = [self.track_waypoints[-1]]
        num_segments: int

        if angle != 0:
            num_segments = max(int(abs(angle) / spacing), 1)
        else:
            num_segments = max(int(distance / spacing), 1)

        delta_angle: float = angle / num_segments
        delta_distance: float = distance / num_segments
        for i in range(1, num_segments + 1):
            segment_pose: Pose3F64 = Pose3F64(
                a_from_b=Isometry3F64([delta_distance, 0, 0], Rotation3F64.Rz(delta_angle)),
                frame_a=segment_poses[-1].frame_b,
                frame_b=f"{next_frame_b}_{i - 1}",
            )
            segment_poses.append(segment_poses[-1] * segment_pose)

        segment_poses[-1].frame_b = next_frame_b
        self.track_waypoints.extend(segment_poses)
        self._segment_indices.append(len(self.track_waypoints))
        self._loaded = False

    def create_straight_segment(self, next_frame_b: str, distance: float, spacing: float = 0.1) -> None:
        """Compute a straight segment."""
        self._create_segment(next_frame_b=next_frame_b, distance=distance, spacing=spacing)

    def create_ab_segment(self, next_frame_b: str, final_pose: Pose3F64, spacing: float = 0.1) -> None:
        """Compute an AB line segment.

        Assumption: We might not be perfectly aligned with thefinal pose, so we need
        to turn in place first.
        """
        initial_pose: Pose3F64 = self.track_waypoints[-1]
        distance: float = np.linalg.norm(initial_pose.a_from_b.translation - final_pose.a_from_b.translation)
        heading_to_next_pose: float = np.arctan2(
            final_pose.a_from_b.translation[0] - initial_pose.a_from_b.translation[0],
            final_pose.a_from_b.translation[1] - initial_pose.a_from_b.translation[1],
        )
        turn_angle: float = np.pi / 2 - heading_to_next_pose - initial_pose.a_from_b.rotation.log()[-1]
        # Turn in place to align with the final pose
        self.create_turn_segment(next_frame_b=next_frame_b, angle=turn_angle, spacing=spacing)
        # Drive straight to the final pose
        self._create_segment(next_frame_b=next_frame_b, distance=distance, spacing=spacing)

    def create_turn_segment(self, next_frame_b: str, angle: float, spacing: float = 0.1) -> None:
        """Compute a turn (in place) segment."""
        self._create_segment(next_frame_b=next_frame_b, distance=0, spacing=spacing, angle=angle)

    def create_arc_segment(self, next_frame_b: str, radius: float, angle: float, spacing: float = 0.1) -> None:
        """Compute an arc segment."""
        arc_length: float = abs(angle * radius)
        self._create_segment(next_frame_b=next_frame_b, distance=arc_length, spacing=spacing, angle=angle)

    def pop_last_segment(self) -> None:
        """Remove the last (appended) segment from the track."""

        if self._loaded:
            print("Cannot pop segment from a loaded track without inserting new segments first.")
            return

        if len(self._segment_indices) > 1:  # Ensure there is a segment to pop
            last_segment_start: int = self._segment_indices[-2]  # Get the start of the last segment
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

    def merge_tracks(self, track_to_merge: Track, threshold: float = 0.5) -> bool:
        """Merge a track with the current track.

        Args:
            track (Track): The track to merge.
        """
        # Calculate the distance from the current track to the beginning and end of the track to merge
        dist_to_current_track = np.linalg.norm(
            self.track_waypoints[-1].a_from_b.translation - track_to_merge.waypoints[0].translation
        )
        if dist_to_current_track > threshold:
            print("Track to merge is too far from the current track, cannot merge.")
            return False

        self.track_waypoints.extend([Pose3F64.from_proto(pose) for pose in track_to_merge.waypoints])
        self._segment_indices.append(len(self.track_waypoints))
        self._loaded = True
        return True

    def reverse_track(self) -> None:
        """Reverse the track."""
        self.track_waypoints = [
            Pose3F64(
                a_from_b=pose.a_from_b * Isometry3F64.Rz(np.pi),
                frame_a=pose.frame_a,
                frame_b=pose.frame_b,
                tangent_of_b_in_a=pose.tangent_of_b_in_a,
            )
            for pose in reversed(self.track_waypoints)
        ]
        self._segment_indices.reverse()
