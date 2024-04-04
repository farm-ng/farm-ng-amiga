"""Example using the track_follower service to drive a pre-recorded track."""
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
import json
from pathlib import Path

from farm_ng.canbus.tool_control_pb2 import ActuatorCommands
from farm_ng.canbus.tool_control_pb2 import HBridgeCommand
from farm_ng.canbus.tool_control_pb2 import HBridgeCommandType
from farm_ng.canbus.tool_control_pb2 import PtoCommand
from farm_ng.canbus.tool_control_pb2 import PtoCommandType
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_client_manager import EventClientSubscriptionManager
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.track.track_pb2 import Track
from farm_ng.track.track_pb2 import TrackFollowerState
from farm_ng.track.track_pb2 import TrackFollowRequest
from google.protobuf.empty_pb2 import Empty


async def set_track(client: EventClient, track: Track) -> None:
    """Set the track of the track_follower.

    Args:
        service_config (EventServiceConfig): The track_follower service config.
        track (Track): The track for the track_follower to follow.
    """
    print(f"Setting track:\n{track}")
    await client.request_reply("/set_track", TrackFollowRequest(track=track))


async def start(client: EventClient) -> None:
    """Follow the track.

    Args:
        service_config (EventServiceConfig): The track_follower service config.
    """
    print("Sending request to start following the track...")
    await client.request_reply("/start", Empty())


async def main(event_manager: EventClientSubscriptionManager, track_path: Path) -> None:
    """Run the track_follower track example. The robot will drive the pre-recorded track.

    Args:
        service_config_path (Path): The path to the track_follower service config.
        track_path: (Path) The filepath of the track to follow.
    """
    # Read the track and package in a Track proto message
    track: Track = proto_from_json_file(track_path, Track())

    # Send the track to the track_follower
    await set_track(event_manager.clients["track_follower"], track)

    # Follow the track
    await start(event_manager.clients["track_follower"])


async def control_tool(event_manager: EventClientSubscriptionManager, tool_state: Path) -> None:
    """Stream the track_follower state.

    Args:
        service_config_path (Path): The path to the track_follower service config.
    """

    # Brief wait to allow the track_follower to start (not necessary in practice)
    await asyncio.sleep(1)

    # create a client to the camera service
    track_follower_client: EventClient = event_manager.clients["track_follower"]
    canbus_client: EventClient = event_manager.clients["canbus"]

    # create dictionary with tool state
    with open(tool_state, "r") as file:
        tool_state: dict[int, bool] = json.load(file)

    message: TrackFollowerState
    async for _, message in track_follower_client.subscribe(
        track_follower_client.subscriptions[0], decode=True, every_n=1
    ):
        current_waypoint = message.progress.closest_waypoint_index
        next_tool_state = tool_state[str(current_waypoint)]
        commands = ActuatorCommands()
        command_type_pto = PtoCommandType.PTO_FORWARD if next_tool_state else PtoCommandType.PTO_STOPPED
        command_type_hbridge = (
            HBridgeCommandType.HBRIDGE_FORWARD if next_tool_state else HBridgeCommandType.HBRIDGE_REVERSE
        )
        commands.pto.append(PtoCommand(id=0, command=command_type_pto, rpm=20.0))
        commands.hbridge.append(HBridgeCommand(id=0, command=command_type_hbridge))
        await canbus_client.request_reply("/control_tools", next_tool_state)


async def run(args) -> None:
    if args.service_config is not None:
        # config with all the configs
        service_config_list: EventServiceConfigList = proto_from_json_file(
            args.service_config, EventServiceConfigList()
        )
        event_manager = EventClientSubscriptionManager(config_list=service_config_list)
        if event_manager is None:
            raise RuntimeError(f"No filter service config in {args.service_config}")

    tasks: list[asyncio.Task] = [
        asyncio.create_task(main(event_manager, args.track)),
        asyncio.create_task(control_tool(event_manager, args.tool_state)),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-track-follower")
    parser.add_argument("--service-config", type=Path, required=True, help="The track_follower service config.")
    parser.add_argument("--track", type=Path, required=True, help="The filepath of the track to follow.")
    parser.add_argument("--tool-state", type=Path, required=True, help="The filepath of the tool states to follow.")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
