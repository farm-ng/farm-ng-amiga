"""Example of requesting the camera calibration from the camera service."""
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
import argparse
import asyncio
from pathlib import Path

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from google.protobuf.empty_pb2 import Empty


async def start_recording(service_config: EventServiceConfig, recording_profile: EventServiceConfig) -> None:
    reply = await EventClient(service_config).request_reply("recorder/start", recording_profile, decode=True)
    print(reply)


async def stop_recording(service_config: EventServiceConfig) -> None:
    reply = await EventClient(service_config).request_reply("recorder/stop", Empty(), decode=True)
    print(reply)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Record logs from the robot.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")

    subparsers = parser.add_subparsers(dest="command")

    start_command = subparsers.add_parser("start_recording", help="Start recording.")
    start_command.add_argument("--recording-profile", type=Path, required=True, help="The recording profile.")

    stop_command = subparsers.add_parser("stop_recording", help="Stop recording.")

    args = parser.parse_args()

    # create a client to the camera service
    service_config: EventServiceConfig = proto_from_json_file(args.service_config, EventServiceConfig())

    if args.command == "start_recording":
        recording_profile = proto_from_json_file(args.recording_profile, EventServiceConfig())
        asyncio.run(start_recording(service_config, recording_profile))

    if args.command == "stop_recording":
        asyncio.run(stop_recording(service_config))
