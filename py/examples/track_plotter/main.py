"""Example plotting a pre-recorded track."""
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
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.pose_pb2 import Pose
from farm_ng.track.track_pb2 import Track
from farm_ng_core_pybind import Pose3F64


def unpack_track(track: Track) -> tuple[list[float], list[float], list[float]]:
    """Unpack a track from a Track proto message into lists of x, y, and heading values.

    Args:
        track: (Track) The Track proto message to unpack.
    Returns:
        x_values: (list[float]) The x values of the track.
        y_values: (list[float]) The y values of the track.
        headings: (list[float]) The heading values of the track.
    """
    x_values: list[float] = []
    y_values: list[float] = []
    headings: list[float] = []

    waypoint: Pose
    for waypoint in track.waypoints:
        goal: Pose3F64 = Pose3F64.from_proto(waypoint)

        x_values.append(goal.translation[0])
        y_values.append(goal.translation[1])
        headings.append(goal.rotation.log()[-1])

    return x_values, y_values, headings


def plot_track(x_values: list[float], y_values: list[float], headings: list[float]) -> None:
    """Plot a track from a Track proto message.

    Args:
        x_values: (list[float]) The x coordinates of the track.
        y_values: (list[float]) The y coordinates of the track.
        headings: (list[float]) The heading values of the track.
    """

    # Plotting
    plt.figure(figsize=(8, 8))

    # Normalize the color scale to the range [0, 1]
    norm = plt.Normalize(0, len(x_values) - 1)
    colors = np.arange(0, len(x_values))

    # Add heading arrows with color scale
    for x, y, heading, color in zip(x_values, y_values, headings, colors):
        dx = np.cos(heading) * 0.05
        dy = np.sin(heading) * 0.05
        plt.arrow(x, y, dx, dy, head_width=0.035, fc=plt.cm.plasma(norm(color)), ec=plt.cm.plasma(norm(color)))

    plt.title('Track waypoints')
    plt.xlabel('X [m]')
    plt.ylabel('Y [m]')

    # Add colorbar below the plot with a smaller height
    cbar = plt.colorbar(
        plt.cm.ScalarMappable(cmap=plt.cm.plasma, norm=norm),
        orientation='horizontal',
        ax=plt.gca(),
        fraction=0.046,
        pad=0.1,
    )
    cbar.set_label('Waypoint idx along the Track')

    plt.grid(True)
    plt.show()


def main(track_path: Path) -> None:
    """Plot a track from a json file containing a Track proto message.

    Args:
        track_path: (Path) The filepath of the track to plot.
    """
    # Read the track and package in a Track proto message
    track: Track = proto_from_json_file(track_path, Track())

    # NOTE: If you have a deprecated FilterTrack proto message instead of a Track proto message,
    # you can convert it to a Track proto message using the following code instead:
    # from farm_ng.filter.filter_pb2 import FilterTrack
    # from farm_ng.track.utils import filter_track_to_track
    # filter_track: FilterTrack = proto_from_json_file(track_path, FilterTrack())
    # track: Track = filter_track_to_track(filter_track)

    # Unpack the track into lists of x, y, and heading values
    x_values, y_values, headings = unpack_track(track)

    # Plot the track
    plot_track(x_values, y_values, headings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga track-plotter example.")
    parser.add_argument("--track", type=Path, required=True, help="The filepath of the track to plot.")
    args = parser.parse_args()

    track_path = Path(args.track).resolve()

    main(track_path)
