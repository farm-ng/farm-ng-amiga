"""Example of setting the camera settings from the service."""
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
from farm_ng.oak import oak_pb2
from google.protobuf.empty_pb2 import Empty


async def main(service_config_path: Path, settings_config_path: Path, stream_name: str) -> None:
    """Request the camera calibration from the camera service.

    Args:
        service_config_path (Path): The path to the camera service config.
        settings_config_path (Path): The path to the camera settings config.
        stream_name (str): The stream name to set the settings for.
    """
    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    # create camera setting from the json file
    camera_settings_request: oak_pb2.CameraSettings | Empty = Empty()
    if settings_config_path:
        camera_settings_request = proto_from_json_file(settings_config_path, oak_pb2.CameraSettings())

    # send a request to the camera service
    # the camera service will reply with the current camera settings
    # available settings are:
    #   - /camera_settings/rgb
    #   - /camera_settings/mono
    camera_settings: oak_pb2.CameraSettings = await EventClient(config).request_reply(
        f"/camera_settings/{stream_name}", camera_settings_request, decode=True
    )

    print(camera_settings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-settings.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera service config.")
    parser.add_argument("--camera-settings", type=Path, required=False, help="The camera control settings.")
    parser.add_argument(
        "--stream-name",
        type=str,
        choices=["rgb", "mono"],
        default="rgb",
        help="The stream name to set the settings for.",
    )
    args = parser.parse_args()

    asyncio.run(main(args.service_config, args.camera_settings, args.stream_name))
