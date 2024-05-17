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
import random
from pathlib import Path

import grpc
from farm_ng.core.event_pb2 import Event
from farm_ng.core.event_service import EventServiceGrpc
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.events_file_reader import proto_from_json_file
from google.protobuf.empty_pb2 import Empty
from google.protobuf.struct_pb2 import Struct


class AgentServer:
    def __init__(self, event_service: EventServiceGrpc) -> None:
        """Initialize the service.

        Args:
            event_service: The event service to use for communication.
        """
        self._event_service = event_service
        self._event_service.add_request_reply_handler(self.request_reply_handler)

        args: dict[str, float] = {}
        for arg in self._event_service.config.args:
            key, value = arg.split("=")
            args[key] = value

        # the rate in hertz to send commands
        self._rate = float(args["rate"])
        self._num_tasks = int(args["num_tasks"])

        self._remainder: int = 1e6

    async def request_reply_handler(self, event: Event, message) -> None:
        """The callback for handling request/reply messages."""
        if event.uri.path == "/update_residual":
            self._remainder = message.value
            self._event_service.logger.info(f"Remainder: {self._remainder}")

        return Empty()

    async def run_task(self, task_id: int) -> None:
        """Run the main task."""
        while True:
            if self._remainder <= 0:
                await asyncio.sleep(0.01)
                continue

            message = Struct()
            message["sample"] = random.random()
            message["task_id"] = task_id

            await self._event_service.publish("/sample", message)
            await asyncio.sleep(1.0 / self._rate)
            print(f"Published sample {message['sample']} from task {task_id}")

    async def serve(self) -> None:
        """Run the service."""
        tasks: list[asyncio.Task] = [asyncio.create_task(self.run_task(i)) for i in range(self._num_tasks)]
        await asyncio.gather(self._event_service.serve(), *tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python agent.py", description="Farm-ng service propagation example agent.")
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
        loop.run_until_complete(AgentServer(event_service).serve())
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        loop.close()
