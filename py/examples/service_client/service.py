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
import argparse
import asyncio
import logging
from pathlib import Path

import grpc
import two_ints_pb2
from farm_ng.core.event_pb2 import Event
from farm_ng.core.event_service import EventServiceGrpc
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from google.protobuf.empty_pb2 import Empty
from google.protobuf.message import Message


class AddTwoIntServer:
    """A simple service that implements the AddTwoInts service."""

    def __init__(self, event_service: EventServiceGrpc) -> None:
        """Initialize the service.

        Args:
            event_service: The event service to use for communication.
        """
        self._event_service = event_service
        self._event_service.add_request_reply_handler(self.request_reply_handler)

    @property
    def logger(self) -> logging.Logger:
        """Return the logger for this service."""
        return self._event_service.logger

    async def request_reply_handler(self, event: Event, message: two_ints_pb2.AddTwoIntsRequest) -> Message:
        """The callback for handling request/reply messages."""
        if event.uri.path == "/sum":
            self.logger.info(f"Requested to sum {message.a} + {message.b}")

            return two_ints_pb2.AddTwoIntsResponse(sum=message.a + message.b)

        return Empty()

    async def serve(self) -> None:
        """Serve the service."""
        await self._event_service.serve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python service.py", description="Farm-ng how to create a service example.")
    parser.add_argument("--service-config", type=Path, required=True, help="The service config.")
    args = parser.parse_args()

    # load the service config
    service_config: EventServiceConfig = proto_from_json_file(args.service_config, EventServiceConfig())

    # create the grpc server
    event_service: EventServiceGrpc = EventServiceGrpc(grpc.aio.server(), service_config)

    loop = asyncio.get_event_loop()

    try:
        # wrap and run the service
        loop.run_until_complete(AddTwoIntServer(event_service).serve())
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        loop.close()
