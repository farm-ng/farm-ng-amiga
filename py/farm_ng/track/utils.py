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

from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.events_file_writer import proto_to_json_file
from farm_ng.filter.filter_pb2 import FilterTrack
from farm_ng.track.track_pb2 import Track

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
