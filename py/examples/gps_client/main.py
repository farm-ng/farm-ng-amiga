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
from farm_ng.gps import gps_pb2


def print_event(event, msg):
    print(f"Event: \n {event} \nMessage: \n {msg}")
    print("-" * 50)


async def main(service_config_path: Path) -> None:
    """Run the gps service client.

    Args:
        service_config_path (Path): The path to the gps service config.
    """
    # create a client to the camera service
    ecef = True
    pvt = True
    relposned = True
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    async for event, msg in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        if isinstance(msg, gps_pb2.RelativePositionFrame) and relposned:
            print_event(event, msg)
            # relposned = False
        elif isinstance(msg, gps_pb2.GpsFrame) and pvt:
            print_event(event, msg)
            # pvt = False
        elif isinstance(msg, gps_pb2.EcefCoordinates) and ecef:
            print_event(event, msg)
            # ecef = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga GPS stream example.")
    parser.add_argument("--service-config", type=Path, required=True, help="The GPS config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
