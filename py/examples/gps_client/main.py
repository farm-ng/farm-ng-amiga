"""Example of a camera service client."""
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
import asyncio
from pathlib import Path

import cv2
import numpy as np
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics
from farm_ng.gps import gps_pb2

def unpack_gps_message(msg: gps_pb2.RelativePositionFrame | gps_pb2.GpsFrame, msg_type: str, _outage_ctn=[0]) -> tuple:
    
    """Unpacks a gps message into a tuple of values.
    Args:
        msg (gps_pb2.RelativePositionFrame | gps_pb2.GpsFrame): The message to unpack.
    Returns:
        tuple: The unpacked message.
    """
    outage_ctn = _outage_ctn[0] # number of consecutive messages with no data

    try: # if the service is active but no messages are being published, the message will be empty

        if msg_type == "relposned":

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

        else:
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

            gps_message = (
                stamp,
                gps_time,
                latitude,
                longitude,
                altitude,
                ground_speed,
                speed_accuracy,
                horizontal_accuracy,
                vertical_accuracy,
                p_dop,
            )
        _outage_ctn[0] = 0
    except AttributeError:
        gps_message = None
        _outage_ctn[0] += 1
        if outage_ctn > 5:
            print("Service is active but no messages are being published. Ensure your GPS antenna is unobstructed and\
                try restarting the service.")
            

    return gps_message

async def main(service_config_path: Path, msg_type: str) -> None:
    """Run the gps service client.

    Args:
        service_config_path (Path): The path to the gps service config.
    """
    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):

        gps_msg = unpack_gps_message(message, msg_type)
        
        if event.uri.path == "/relposned" and msg_type == 'relposned':
            print(f"Message stamp: {gps_msg[0]}")
            print(f"GPS time: {gps_msg[1]}")
            print(f"Relative pose north: {gps_msg[2]}")
            print(f"Relative pose east: {gps_msg[3]}")
            print(f"Relative pose down: {gps_msg[4]}")
            print(f"Relative pose length: {gps_msg[5]}")
            print(f"Accuracy north: {gps_msg[6]}")
            print(f"Accuracy east: {gps_msg[7]}")
            print(f"Accuracy down: {gps_msg[8]}")
            print(f"Carr soln: {gps_msg[9]}")
            print(f"GNSS fix ok: {gps_msg[10]}\n################################")

        elif event.uri.path == "/pvt" and msg_type == 'pvt':
            print(f"Message stamp: {gps_msg[0]}")
            print(f"GPS time: {gps_msg[1]}")
            print(f"Latitude: {gps_msg[2]}")
            print(f"Longitude: {gps_msg[3]}")
            print(f"Altitude: {gps_msg[4]}")
            print(f"Ground speed: {gps_msg[5]}")
            print(f"Speed accuracy: {gps_msg[6]}")
            print(f"Horizontal accuracy: {gps_msg[7]}")
            print(f"Vertical accuracy: {gps_msg[8]}")
            print(f"P dop: {gps_msg[9]}\n################################")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-gps-stream")
    parser.add_argument("--service-config", type=Path, required=True, help="The GPS config.")
    parser.add_argument(
    "--msg-type", type=str, default="relposned", help="The name of the gps interface to read: relposned or pvt."
    )
    args = parser.parse_args()

    asyncio.run(main(args.service_config, args.msg_type))
