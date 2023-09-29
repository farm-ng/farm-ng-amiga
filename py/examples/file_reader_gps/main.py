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

from farm_ng.core.events_file_reader import build_events_dict
from farm_ng.core.events_file_reader import EventLogPosition
from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.gps import gps_pb2


def print_relative_position_frame(msg):
    print(f"Message stamp: {msg.stamp.stamp}")
    print(f"GPS time: {msg.gps_time.stamp}")
    print(f"Relative pose north: {msg.relative_pose_north}")
    print(f"Relative pose east: {msg.relative_pose_east}")
    print(f"Relative pose down: {msg.relative_pose_down}")
    print(f"Relative pose length: {msg.relative_pose_length}")
    print(f"Accuracy north: {msg.accuracy_north}")
    print(f"Accuracy east: {msg.accuracy_east}")
    print(f"Accuracy down: {msg.accuracy_down}")
    print(f"Carrier solution: {msg.carr_soln}")
    print(f"GNSS fix ok: {msg.gnss_fix_ok}")
    print("-" * 50)


def print_gps_frame(msg):
    print(f"Message stamp: {msg.stamp.stamp}")
    print(f"GPS time: {msg.gps_time.stamp}")
    print(f"Latitude: {msg.latitude}")
    print(f"Longitude: {msg.longitude}")
    print(f"Altitude: {msg.altitude}")
    print(f"Ground speed: {msg.ground_speed}")
    print(f"Speed accuracy: {msg.speed_accuracy}")
    print(f"Horizontal accuracy: {msg.horizontal_accuracy}")
    print(f"Vertical accuracy: {msg.vertical_accuracy}")
    print(f"P DOP: {msg.p_dop}")
    print("-" * 50)


def main(file_name: str, uri_path: str) -> None:
    if uri_path is not None and uri_path not in ["/relposned", "/pvt"]:
        raise RuntimeError(f"Uri path type not recognized: {uri_path}")

    # create the file reader
    reader = EventsFileReader(file_name)
    success: bool = reader.open()
    if not success:
        raise RuntimeError(f"Failed to open events file: {file_name}")

    # get the index of the events file
    events_index: list[EventLogPosition] = reader.get_index()

    # structure the index as a dictionary of lists of events
    events_dict: dict[str, list[EventLogPosition]] = build_events_dict(events_index)
    print(f"All available topics: {sorted(events_dict.keys())}")

    if uri_path is not None:
        gps_events = events_dict[f"/gps{uri_path}"]
        print(f"Found {len(gps_events)} packets of gps{uri_path}\n")
    else:
        gps_events = events_dict["/gps/relposned"] + events_dict["/gps/pvt"]
        print(f"Found {len(gps_events)} packets of /gps/\n")

    for event_log in gps_events:

        # parse the message
        msg: gps_pb2.RelativePositionFrame | gps_pb2.GpsFrame = event_log.read_message()
        if not uri_path or event_log.event.uri.path == f"gps{uri_path}":
            if isinstance(msg, gps_pb2.RelativePositionFrame):
                print_relative_position_frame(msg)
            elif isinstance(msg, gps_pb2.GpsFrame):
                print_gps_frame(msg)

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file reader example for parsing GPS messages.")
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    parser.add_argument("--uri-path", type=str, help="The name of the gps interface to read: /relposned or /pvt.")
    args = parser.parse_args()
    main(args.file_name, args.uri_path)
