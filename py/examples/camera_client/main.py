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
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics


@dataclass
class TimeStampHistory:
    device_sample: float = 0.0
    driver_receive: float = 0.0
    service_send: float = 0.0
    client_receive: float = 0.0
    loop_start: float = 0.0
    stamps: float = 0.0
    decode: float = 0.0
    process: float = 0.0
    display: float = 0.0

    def debug(self):
        print(f"Total: {int((self.display - self.device_sample)*1000)} ms")
        print(
            " | ".join(
                [
                    f"POE: {int((self.driver_receive - self.device_sample)*1000)} ms",
                    f"Service: {int((self.service_send - self.driver_receive)*1000)} ms",
                    f"Transmit: {int((self.client_receive - self.service_send)*1000)} ms",
                    f"Start: {int((self.loop_start - self.client_receive)*1000)} ms",
                ]
            )
        )
        print(
            " | ".join(
                [
                    f"Stamp: {int((self.stamps - self.loop_start)*1000)} ms",
                    f"Decode: {int((self.decode - self.stamps)*1000)} ms",
                    f"Process: {int((self.process - self.decode)*1000)} ms",
                    f"Display: {int((self.display - self.process)*1000)} ms",
                ]
            )
        )


async def main(service_config_path: Path, proc_time_ms: int, fullscreen: bool):
    """Run the camera service client.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    # Create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    last: float = time.monotonic()
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        start = time.monotonic()
        # Unpack timestamp history
        stamp_log = TimeStampHistory()
        stamp_log.device_sample = message.meta.timestamp
        stamp_log.driver_receive = message.meta.timestamp_recv
        stamp_log.service_send = get_stamp_by_semantics_and_clock_type(event, StampSemantics.SERVICE_SEND, "monotonic")
        stamp_log.client_receive = get_stamp_by_semantics_and_clock_type(
            event, StampSemantics.CLIENT_RECEIVE, "monotonic"
        )
        stamp_log.loop_start = start
        stamp_log.stamps = time.monotonic()

        # Cast image data bytes to numpy and decode
        image = cv2.imdecode(np.frombuffer(message.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)
        if event.uri.path == "/disparity":
            image = cv2.applyColorMap(image * 3, cv2.COLORMAP_JET)
        stamp_log.decode = time.monotonic()

        # Here we fake some processing time
        await asyncio.sleep(proc_time_ms / 1000.0)
        stamp_log.process = time.monotonic()

        # Visualize the image
        cv2.namedWindow("image", cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)
        cv2.imshow("image", image)
        cv2.waitKey(1)
        stamp_log.display = time.monotonic()

        print(f"Rate: {1/(time.monotonic() - last):.2f} Hz")
        stamp_log.debug()
        print("###################\n")
        last = time.monotonic()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-stream.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    parser.add_argument("--proc-time-ms", type=float, default=0.0, help="The fake processing time.")
    parser.add_argument("--fullscreen", action="store_true", help="Display in fullscreen mode.")

    args = parser.parse_args()

    asyncio.run(main(args.service_config, args.proc_time_ms, args.fullscreen))
