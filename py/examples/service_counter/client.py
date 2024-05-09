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
"""A simple program that implements a counter service."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.uri_pb2 import Uri
from google.protobuf.empty_pb2 import Empty


class CounterClient:
    def __init__(self, service_config: EventServiceConfig) -> None:
        """Initialize the client.

        Args:
            service_config: The service config.
        """
        self._event_client = EventClient(service_config)

    async def subscribe(self) -> None:
        """Run the main task."""
        async for event, message in self._event_client.subscribe(
            request=SubscribeRequest(uri=Uri(path="/counter"), every_n=1), decode=True
        ):
            print(f"Received message: {message}")


async def command_subscribe(client: CounterClient) -> None:
    """Subscribe to the counter service."""
    await client.subscribe()


async def command_reset(client: CounterClient) -> None:
    """Reset the counter."""
    await client._event_client.request_reply("/reset_counter", Empty())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python client.py", description="Farm-ng client to the counter-service example."
    )
    parser.add_argument("--service-config", type=Path, required=True, help="The service config.")

    sub_parsers = parser.add_subparsers(dest="command")
    sub_parsers.add_parser("subscribe", help="Subscribe to the counter service.")
    sub_parsers.add_parser("reset", help="Reset the counter.")

    args = parser.parse_args()

    # load the service config
    service_config: EventServiceConfig = proto_from_json_file(args.service_config, EventServiceConfig())

    client = CounterClient(service_config)

    if args.command == "subscribe":
        asyncio.run(command_subscribe(client))
    elif args.command == "reset":
        asyncio.run(command_reset(client))
    else:
        import sys

        parser.print_help()
        sys.exit(1)
