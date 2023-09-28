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


def main(file_name: str, msg_type: str) -> None:
    if msg_type not in ["relposned", "pvt"]:
        raise RuntimeError(f"Message type not recognized: {msg_type}")

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

    gps_events = events_dict[f"/gps/{msg_type}"]
    print(f"Found {len(gps_events)} packets of gps/{msg_type}\n")

    for event_log in gps_events:

        # parse the message
        msg: gps_pb2.RelativePositionFrame | gps_pb2.GpsFrame = event_log.read_message()

        if msg_type == "pvt":
            stamp: float = msg.stamp.stamp
            gps_time: float = msg.gps_time.stamp
            latitude: float = msg.latitude
            longitude: float = msg.longitude
            altitude: float = msg.altitude
            ground_speed: float = msg.ground_speed
            speed_accuracy: float = msg.speed_accuracy
            horizontal_accuracy: float = msg.horizontal_accuracy
            vertical_accuracy: float = msg.vertical_accuracy
            p_dop: float = msg.p_dop

            print(f"Message stamp: {stamp}")
            print(f"GPS time: {gps_time}")
            print(f"Latitude: {latitude}")
            print(f"Longitude: {longitude}")
            print(f"Altitude: {altitude}")
            print(f"Ground speed: {ground_speed}")
            print(f"Speed accuracy: {speed_accuracy}")
            print(f"Horizontal accuracy: {horizontal_accuracy}")
            print(f"Vertical accuracy: {vertical_accuracy}")
            print(f"P dop: {p_dop}\n################################")

        elif msg_type == "relposned":
            stamp: float = msg.stamp.stamp
            gps_time: float = msg.gps_time.stamp
            relative_pose_north: float = msg.relative_pose_north
            relative_pose_east: float = msg.relative_pose_east
            relative_pose_down: float = msg.relative_pose_down
            relative_pose_length: float = msg.relative_pose_length
            accuracy_north: float = msg.accuracy_north
            accuracy_east: float = msg.accuracy_east
            accuracy_down: float = msg.accuracy_down
            carr_soln: int = msg.carr_soln
            gnss_fix_ok: bool = msg.gnss_fix_ok

            print(f"Message stamp: {stamp}")
            print(f"GPS time: {gps_time}")
            print(f"Relative pose north: {relative_pose_north}")
            print(f"Relative pose east: {relative_pose_east}")
            print(f"Relative pose down: {relative_pose_down}")
            print(f"Relative pose length: {relative_pose_length}")
            print(f"Accuracy north: {accuracy_north}")
            print(f"Accuracy east: {accuracy_east}")
            print(f"Accuracy down: {accuracy_down}")
            print(f"Carrier solution: {carr_soln}")
            print(f"GNSS fix ok: {gnss_fix_ok}\n################################")

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file reader example for parsing GPS messages.")
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    parser.add_argument(
        "--msg-type", type=str, default="relposned", help="The name of the gps interface to read: relposned or pvt."
    )
    args = parser.parse_args()
    main(args.file_name, args.msg_type)
