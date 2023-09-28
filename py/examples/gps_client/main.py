"""Example of a GPS service client."""
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

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file


async def main(service_config_path: Path, msg_type: str, _outage_ctn=[0]) -> None:
    """Run the gps service client.

    Args:
        service_config_path (Path): The path to the gps service config.
    """
    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    async for event, msg in EventClient(config).subscribe(config.subscriptions[0]):

        try:
            if event.uri.path == "/relposned" and msg_type == 'relposned':
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
                print(f"GNSS fix ok: {msg.gnss_fix_ok}\n################################")

            elif event.uri.path == "/pvt" and msg_type == 'pvt':
                print(f"Message stamp: {msg.stamp.stamp}")
                print(f"GPS time: {msg.gps_time.stamp}")
                print(f"Latitude: {msg.latitude}")
                print(f"Longitude: {msg.longitude}")
                print(f"Altitude: {msg.altitude}")
                print(f"Ground speed: {msg.ground_speed}")
                print(f"Speed accuracy: {msg.speed_accuracy}")
                print(f"Horizontal accuracy: {msg.horizontal_accuracy}")
                print(f"Vertical accuracy: {msg.vertical_accuracy}")
                print(f"P DOP: {msg.p_dop}\n################################")

        except AttributeError:
            _outage_ctn[0] += 1
            if _outage_ctn[0] > 0:
                print(
                    "Service is active but no messages are being published. "
                    "Ensure your GPS antenna is unobstructed and "
                    "try restarting the service."
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-gps-stream")
    parser.add_argument("--service-config", type=Path, required=True, help="The GPS config.")
    parser.add_argument(
        "--msg-type", type=str, default="relposned", help="The name of the gps interface to read: relposned or pvt."
    )
    args = parser.parse_args()

    asyncio.run(main(args.service_config, args.msg_type))
