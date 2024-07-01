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

import time
import numpy as np
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics


async def main(service_config_path: Path) -> None:
    """Run the camera service client.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    start = time.monotonic()
    last_stamp: float | None = None
    missed_frames = 0

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        # Find the monotonic driver receive timestamp, or the first timestamp if not available.
        now = time.monotonic()
        if last_stamp is None:
            last_stamp = now
        
        # We expected frames at 10 fps, so we should see a frame every 0.1 seconds.
        if now - last_stamp > 3 * (1.0/10.0):
            missed_frames += 1
            
        
        elif now - last_stamp > 3.0:
            print(f"Stopping after: {now - start}")
            print(f"Missed frames: {missed_frames}")
            break
        
        if event.timestamps is not None:
            last_stamp = now

        time_elapsed = now - start
        time_formatted = time.strftime("%H:%M:%S", time.gmtime(time_elapsed))
        print(f"Total time elapsed: {time_formatted}")
            


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-stream.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
