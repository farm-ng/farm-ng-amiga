"""Example of for recording a track, using the filter service client."""
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
from farm_ng.core.events_file_writer import proto_to_json_file
from farm_ng.core.pose_pb2 import Pose
from farm_ng.track.track_pb2 import Track
from google.protobuf.empty_pb2 import Empty


async def main(service_config_path: Path, track_name: str, output_dir: Path) -> None:
    """Run the filter service client to record a track.

    Args:
        service_config_path (Path): The path to the filter service config.
        track_name (str): The name of the track.
        output_dir (Path): The directory to save the track to.
    """
    # create a client to the filter service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    # Clear the track so everything going forward is tracked
    await EventClient(config).request_reply("/clear_track", Empty())

    # Create a Track message to store the waypoints in
    track: Track = Track()

    # Subscribe to the filter track topic
    message: Pose
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        print("###################")
        print("Adding to track:")
        print(message)

        # Add the pose to the Track message
        next_waypoint = track.waypoints.add()
        next_waypoint.CopyFrom(message)

        # Write the Track to disk, overwriting the file each time
        if not proto_to_json_file(output_dir / f"{track_name}.json", track):
            raise RuntimeError(f"Failed to write Track to {output_dir}")

        print(f"Saved track of length {len(track.waypoints)} to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga track recording example.")
    parser.add_argument("--service-config", type=Path, required=True, help="The filter service config.")
    parser.add_argument("--track-name", type=str, required=True, help="The name of the track.")
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).parent, help="The directory to save the track to."
    )
    args = parser.parse_args()

    if not args.output_dir.exists() or not args.output_dir.is_dir():
        raise ValueError(f"Invalid output directory: {args.output_dir}")

    if not args.track_name:
        raise ValueError("No track name provided.")

    asyncio.run(main(args.service_config, args.track_name, args.output_dir))
