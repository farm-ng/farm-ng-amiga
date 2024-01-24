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

from farm_ng.canbus.tool_control_pb2 import ToolStatuses
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from google.protobuf.empty_pb2 import Empty


async def main(service_config_path: Path) -> None:
    """Run the camera service client.

    Args:
        service_config_path (Path): The path to the camera service config.
    """

    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    client: EventClient = EventClient(config)

    print(client.config)

    tool_statuses: ToolStatuses
    while True:
        # Update and send the twist command
        print("Requesting tool status")
        tool_statuses = await client.request_reply("/get_tool_statuses", Empty(), decode=True)

        if not isinstance(tool_statuses, ToolStatuses):
            raise TypeError(f"Expected ToolStatuses, got {type(tool_statuses)}")

        print(tool_statuses)

        # Sleep to limit the query rate
        await asyncio.sleep(0.2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Query for the ToolStatuses from the canbus service.")
    parser.add_argument("--service-config", type=Path, required=True, help="The canbus service config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
