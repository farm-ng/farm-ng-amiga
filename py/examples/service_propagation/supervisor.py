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
"""A simple program that implements the AddTwoInts service."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import grpc
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service import EventServiceGrpc
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.events_file_reader import proto_from_json_file
from google.protobuf.empty_pb2 import Empty


class SupervisorServer:
    def __init__(self, event_service: EventServiceGrpc, config_list: EventServiceConfigList) -> None:
        """Initialize the service.

        Args:
            event_service: The event service to use for communication.
        """
        self._event_service = event_service

        self._clients: dict[str, EventClient] = {
            config.name: EventClient(config)
            for config in config_list.configs
            if config.name != event_service.config.name
        }

        args: dict[str, float] = {}
        for arg in self._event_service.config.args:
            key, value = arg.split("=")
            args[key] = value

        # the rate in hertz to send commands
        self._confidence = float(args["confidence"])

    async def subscribe(self, subscripton) -> None:
        """Run the main task."""
        # create the event client
        service_name = subscripton.uri.query.split("=")[-1]
        client = self._clients[service_name]

        async for event, message in client.subscribe(subscripton, decode=True):
            if message["sample"] > self._confidence:
                residual = await self._clients["storage"].request_reply("/update_storage", Empty(), decode=True)
                self._event_service.logger.info(f"Residual: {residual}")
                await client.request_reply("/update_residual", residual)

    async def serve(self) -> None:
        """Run the service."""
        tasks: list[asyncio.Task] = []
        for subscription in self._event_service.config.subscriptions:
            tasks.append(asyncio.create_task(self.subscribe(subscription)))
        await asyncio.gather(self._event_service.serve(), *tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python supervisor.py", description="Farm-ng service propagation example supervisor."
    )
    parser.add_argument("--service-config", type=Path, required=True, help="The service list config.")
    parser.add_argument("--service-name", type=str, required=True, help="The service name.")
    args = parser.parse_args()

    # load the service config
    config_list: EventServiceConfigList = proto_from_json_file(args.service_config, EventServiceConfigList())

    service_config: EventServiceConfig | None = None
    for config in config_list.configs:
        if config.name == args.service_name:
            service_config = config
            break

    if service_config is None:
        raise RuntimeError(f"Service '{args.service_name}' not found in config.")

    # create the grpc server
    event_service: EventServiceGrpc = EventServiceGrpc(grpc.aio.server(), service_config)

    loop = asyncio.get_event_loop()

    try:
        # wrap and run the service
        loop.run_until_complete(SupervisorServer(event_service, config_list).serve())
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        loop.close()
