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
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics
from farm_ng.gps import gps_pb2


def print_relative_position_frame(msg):
    """Prints the relative position frame message.

    Args: msg: The relative position frame message.
    """
    print("RELATIVE POSITION FRAME \n")
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
    """Prints the gps frame message.

    Args: msg: The gps frame message.
    """
    print("PVT FRAME \n")
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


def print_ecef_frame(msg):
    """Prints the ecef frame message.

    Args: msg: The ecef frame message.
    """
    print("ECEF FRAME \n")
    print(f"Message stamp: {msg.stamp.stamp}")
    print(f"GPS time: {msg.gps_time.stamp}")
    print(f"x: {msg.x}")
    print(f"y: {msg.y}")
    print(f"z: {msg.z}")
    print(f"Accuracy: {msg.accuracy}")
    print(f"Flags: {msg.flags}")
    print("-" * 50)


def main(file_name: str, topic_name: str) -> None:
    if topic_name not in [None, "relposned", "pvt", "ecef"]:
        raise RuntimeError(f"Topic name not recognized: {topic_name}")

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

    if topic_name is not None:
        gps_events = events_dict[f"/gps/{topic_name}"]
        print(f"Found {len(gps_events)} packets of gps/{topic_name}\n")
    else:
        relposned_events = events_dict["/gps/relposned"]
        print(f"Found {len(relposned_events)} packets of /gps/relposned\n")
        pvt_events = events_dict["/gps/pvt"]
        print(f"Found {len(pvt_events)} packets of /gps/pvt\n")
        ecef_events = events_dict["/gps/ecef"]
        print(f"Found {len(ecef_events)} packets of /gps/ecef\n")
        gps_events = relposned_events + pvt_events + ecef_events

        # Sort the pvt and relposned events by the DRIVER_RECEIVE timestamp
        # DRIVER_RECEIVE is the monotonic time the GPS service on the amiga brain
        # received the message from the GPS receiver.
        gps_events = sorted(
            gps_events,
            key=lambda event_log: get_stamp_by_semantics_and_clock_type(
                event_log.event, StampSemantics.DRIVER_RECEIVE, "monotonic"
            ),
        )

    for event_log in gps_events:
        # parse the message
        msg: gps_pb2.RelativePositionFrame | gps_pb2.GpsFrame = event_log.read_message()
        if isinstance(msg, gps_pb2.RelativePositionFrame):
            print_relative_position_frame(msg)
        elif isinstance(msg, gps_pb2.GpsFrame):
            print_gps_frame(msg)
        elif isinstance(msg, gps_pb2.EcefCoordinates):
            print_ecef_frame(msg)

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python main.py", description="Event file reader example for parsing GPS messages."
    )
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    parser.add_argument(
        "--topic-name",
        type=str,
        help="The name of the gps interface to print: `relposned`, `pvt`, or `ecef`. Default is both topics.",
    )
    args = parser.parse_args()
    main(args.file_name, args.topic_name)
