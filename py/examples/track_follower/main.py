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
from pathlib import Path

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.track.track_pb2 import Track
from farm_ng.track.track_pb2 import TrackFollowerState
from farm_ng.track.track_pb2 import TrackFollowRequest
from google.protobuf.empty_pb2 import Empty


async def set_track(service_config: EventServiceConfig, track: Track) -> None:
    """Set the track of the track_follower.

    Args:
        service_config (EventServiceConfig): The track_follower service config.
        track (Track): The track for the track_follower to follow.
    """
    print(f"Setting track:\n{track}")
    await EventClient(service_config).request_reply("/set_track", TrackFollowRequest(track=track))


async def start(service_config: EventServiceConfig) -> None:
    """Follow the track.

    Args:
        service_config (EventServiceConfig): The track_follower service config.
    """
    print("Sending request to start following the track...")
    await EventClient(service_config).request_reply("/start", Empty())


async def main(service_config_path: Path, track_path: Path) -> None:
    """Run the track_follower track example. The robot will drive the pre-recorded track.

    Args:
        service_config_path (Path): The path to the track_follower service config.
        track_path: (Path) The filepath of the track to follow.
    """

    # Extract the track_follower service config from the JSON file
    service_config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    # Read the track and package in a Track proto message
    track: Track = proto_from_json_file(track_path, Track())

    # Send the track to the track_follower
    await set_track(service_config, track)

    # Follow the track
    await start(service_config)


async def stream_track_state(service_config_path: Path) -> None:
    """Stream the track_follower state.

    Args:
        service_config_path (Path): The path to the track_follower service config.
    """

    # Brief wait to allow the track_follower to start (not necessary in practice)
    await asyncio.sleep(1)
    print("Streaming track_follower state...")

    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    message: TrackFollowerState
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        print("###################")
        print(message)


async def run(args) -> None:
    tasks: list[asyncio.Task] = [
        asyncio.create_task(main(args.service_config, args.track)),
        asyncio.create_task(stream_track_state(args.service_config)),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga track-follower example.")
    parser.add_argument("--service-config", type=Path, required=True, help="The track_follower service config.")
    parser.add_argument("--track", type=Path, required=True, help="The filepath of the track to follow.")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
