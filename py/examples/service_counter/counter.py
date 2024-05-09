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
from farm_ng.core.event_pb2 import Event
from farm_ng.core.event_service import EventServiceGrpc
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from google.protobuf.empty_pb2 import Empty
from google.protobuf.message import Message
from google.protobuf.wrappers_pb2 import Int32Value


class CounterServer:
    def __init__(self, event_service: EventServiceGrpc) -> None:
        """Initialize the service.

        Args:
            event_service: The event service to use for communication.
        """
        self._event_service = event_service
        self._event_service.add_request_reply_handler(self.request_reply_handler)

        self._counter: int = 0
        self._rate: float = 1.0

    async def request_reply_handler(self, event: Event, message: Message) -> None:
        """The callback for handling request/reply messages."""
        if event.uri.path == "/reset_counter":
            self._counter = 0

        return Empty()

    async def run(self) -> None:
        """Run the main task."""
        while True:
            await self._event_service.publish("/counter", Int32Value(value=self._counter))
            self._counter += 1
            await asyncio.sleep(1.0 / self._rate)

    async def serve(self) -> None:
        await asyncio.gather(self._event_service.serve(), self.run())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python counter.py", description="Farm-ng counter service example.")
    parser.add_argument("--service-config", type=Path, required=True, help="The service list config.")
    args = parser.parse_args()

    # load the service config
    service_config: EventServiceConfig = proto_from_json_file(args.service_config, EventServiceConfig)

    # create the grpc server
    event_service: EventServiceGrpc = EventServiceGrpc(grpc.aio.server(), service_config)

    loop = asyncio.get_event_loop()

    try:
        # wrap and run the service
        loop.run_until_complete(CounterServer(event_service).serve())
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        loop.close()
