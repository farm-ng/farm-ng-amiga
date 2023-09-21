"""A simple program that implements the AddTwoInts service."""
import argparse
import asyncio
from pathlib import Path
import grpc
import logging

from farm_ng.core.event_service import EventServiceGrpc
from farm_ng.core.event_service_pb2 import (
    EventServiceConfig,
    RequestReplyRequest,
)
from farm_ng.core.events_file_reader import (
    payload_to_protobuf,
    proto_from_json_file,
)

from google.protobuf.message import Message
from google.protobuf.empty_pb2 import Empty

from two_ints_pb2 import AddTwoIntsResponse


class AddTwoIntServer:
    """A simple service that implements the AddTwoInts service."""
    def __init__(self, event_service: EventServiceGrpc) -> None:
        """Initialize the service.
        
        Args:
            event_service: The event service to use for communication.
        """
        self._event_service = event_service
        # TODO: improve by self._event_service.add_request_reply_handler(self.request_reply_handler)
        self._event_service.request_reply_handler = self.request_reply_handler
    
    @property
    def logger(self) -> logging.Logger:
        """Return the logger for this service."""
        return self._event_service.logger

    async def request_reply_handler(
        self,
        request: RequestReplyRequest,
    ) -> Message:
        """The callback for handling request/reply messages."""

        # decode the requested message
        request_message: two_ints_pb2.AddTwoIntsRequest = payload_to_protobuf(
            request.event, request.payload
        )

        if request.event.uri.path == "/sum":
            self.logger.info(f"Requested to sum {request_message.a} + {request_message.b}")

            return AddTwoIntsResponse(sum=request_message.a + request_message.b)
        
        return Empty()
    
    async def serve(self) -> None:
        """Serve the service."""
        await self._event_service.serve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="farm-ng-service")
    parser.add_argument("--service-config", type=Path, required=True, help="The service config.")
    args = parser.parse_args()

    # load the service config
    service_config: EventServiceConfig = proto_from_json_file(
        args.service_config, EventServiceConfig())

    # create the grpc server
    event_service: EventServiceGrpc = EventServiceGrpc(
        grpc.aio.server(), service_config
    )

    loop = asyncio.get_event_loop()
    
    try:
        # wrap and run the service
        loop.run_until_complete(AddTwoIntServer(event_service).serve())
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        loop.close()