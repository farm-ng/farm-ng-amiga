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

from farm_ng.control.control_pb2 import ControllerTrack
from farm_ng.filter.filter_pb2 import FilterTrack


def filter_track_to_controller_track(filter_track: FilterTrack) -> ControllerTrack:
    """Converts a FilterTrack to a ControllerTrack.

    Args:
        filter_track: A FilterTrack.
    Returns:
        A ControllerTrack.
    """
    return ControllerTrack(name=filter_track.name, poses=[state.pose for state in filter_track.states])
