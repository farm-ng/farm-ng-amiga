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


async def main(service_config_path: Path) -> None:
    """Run the camera service client.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    # Create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        # Find the monotonic driver receive timestamp, or the first timestamp if not available.
        stamp = (
            get_stamp_by_semantics_and_clock_type(event, StampSemantics.DRIVER_RECEIVE, "monotonic")
            or event.timestamps[0].stamp
        )

        # Print the timestamp and metadata
        print(f"Timestamp: {stamp}\n")
        print(f"Meta: {message.meta}")
        print("###################\n")

        # "RAW" images only have /rgb and /left, no /right or /disparity
        image = None
        if event.uri.path == "/rgb":
            width, height = (1920, 1080)
        elif event.uri.path == "/left":
            width, height = (1280, 800)
        else:
            print(f"Unknown image type: {event.uri.path}")
            continue

        try:
            image = np.frombuffer(message.data, dtype=np.uint8).reshape((height, width, 3))
        except ValueError as e:
            print(f"Error: {e}")
            continue

        if image is not None:
            # Visualize the image
            cv2.namedWindow("image", cv2.WINDOW_NORMAL)
            cv2.imshow("image", image)
            cv2.waitKey(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-stream.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
