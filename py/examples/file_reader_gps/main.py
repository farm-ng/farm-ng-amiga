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


def unpack_gps_message(msg: gps_pb2.RelativePositionFrame) -> tuple:
    """Unpacks a gps_pb2.RelativePositionFrame message into a list of values.

    Args:
        msg (gps_pb2.RelativePositionFrame): The message to unpack.
    Returns:
        tuple: The unpacked message.
    """

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

    gps_message = (
        stamp,
        gps_time,
        relative_pose_north,
        relative_pose_east,
        relative_pose_down,
        relative_pose_length,
        accuracy_north,
        accuracy_east,
        accuracy_down,
        carr_soln,
        gnss_fix_ok,
    )

    return gps_message


def main(file_name: str, gps_interface: str) -> None:
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

    gps_events = events_dict["/gps/relposned"]
    print(f"Found {len(gps_events)} packets of gps_pb2.RelativePositionFrame\n")

    for event_log in gps_events:

        # parse the message
        msg: gps_pb2.RelativePositionFrame = event_log.read_message()
        gps_msg = unpack_gps_message(msg)
        print(
            f"Message stamp: {gps_msg[0]}, GPS time: {gps_msg[1]}, "
            f"Relative pose north: {gps_msg[2]}, Relative pose east: {gps_msg[3]}, "
            f"Relative pose down: {gps_msg[4]}, Relative pose length: {gps_msg[5]},"
            f"Accuracy north: {gps_msg[6]}, Accuracy east: {gps_msg[7]}, "
            f"Accuracy down: {gps_msg[8]}, Carr soln: {gps_msg[9]}, "
            f"GNSS fix ok: {gps_msg[10]}\n"
        )

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file reader example for parsing GPS messages.")
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    parser.add_argument(
        "--gps-interface", type=str, default="relposed", help="The name of the gps interface to read: relposned or pvt."
    )
    args = parser.parse_args()
    main(args.file_name, args.gps_interface)
