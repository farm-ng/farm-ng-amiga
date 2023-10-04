"""Example using the controller service to drive a pre-recorded track."""
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

from farm_ng.control.control_pb2 import ControllerState
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.filter.filter_pb2 import FilterTrack
from farm_ng_core_pybind import Pose3F64
from google.protobuf.empty_pb2 import Empty
from google.protobuf.wrappers_pb2 import StringValue


async def get_pose(service_config: EventServiceConfig) -> Pose3F64:
    """Get the current pose of the robot in the world frame, from the controller service.

    Args:
        service_config (EventServiceConfig): The controller service config.
    """
    reply = await EventClient(service_config).request_reply("/get_pose", Empty(), decode=True)
    print(f"Current pose:\n{reply}")
    return Pose3F64.from_proto(reply)


async def set_track(service_config: EventServiceConfig, filter_track: FilterTrack) -> None:
    """Set the track of the controller.

    WARNING: This API will change in the future.
    The controller service currently expects a FilterTrack proto message,
    but this will change in the future to a more general message type.

    Args:
        service_config (EventServiceConfig): The controller service config.
        filter_track (FilterTrack): The track for the controller to follow.
    """
    print(f"Setting track:\n{filter_track}")
    await EventClient(service_config).request_reply("/set_track", filter_track)


async def follow_track(service_config: EventServiceConfig) -> None:
    """Follow the track.

    Args:
        service_config (EventServiceConfig): The controller service config.
    """
    print("Following track...")
    await EventClient(service_config).request_reply("/follow_track", StringValue(value="my_custom_track"))


async def main(service_config_path: Path, track_path: Path) -> None:
    """Run the controller track example. The robot will drive the pre-recorded track.

    Args:
        service_config_path (Path): The path to the controller service config.
    """

    # Extract the controller service config from the JSON file
    service_config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    # Build the track and package in a FilterTrack proto message
    filter_track: FilterTrack = proto_from_json_file(track_path, FilterTrack())

    # Send the track to the controller
    await set_track(service_config, filter_track)

    # Follow the track
    await follow_track(service_config)


async def stream_controller_state(service_config_path: Path) -> None:
    """Stream the controller state.

    Args:
        service_config_path (Path): The path to the controller service config.
    """

    # Brief wait to allow the controller to start (not necessary in practice)
    await asyncio.sleep(1)
    print("Streaming controller state...")

    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    message: ControllerState
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        print("###################")
        print(message)


async def run(args) -> None:
    tasks: list[asyncio.Task] = [
        asyncio.create_task(main(args.service_config, args.side_length)),
        asyncio.create_task(stream_controller_state(args.service_config)),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-controller-track")
    parser.add_argument("--service-config", type=Path, required=True, help="The controller service config.")
    parser.add_argument("--track", type=Path, required=True, help="The filepath of the track to follow.")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
