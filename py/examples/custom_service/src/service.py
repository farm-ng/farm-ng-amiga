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
import argparse
import asyncio
import logging

import grpc
import two_ints_pb2
import two_ints_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# TODO: subclass ServiceGrpc
class AddTwoIntsServiceGrpc:
    def __init__(self, server: grpc.aio.server, port: int) -> None:
        # TODO: define where to place this in the base class
        self.server = server
        self.server.add_insecure_port(f"[::]:{port}")

        logger.info(f"Starting the service on port {port}...")

        # NOTE: this need to be added every time a new service is added
        two_ints_pb2_grpc.add_AddTwoIntsServiceServicer_to_server(self, self.server)

    # NOTE: this should be part of the base class
    async def serve(self) -> None:
        logger.info("Starting compost_spreader server")
        await self.server.start()
        logger.info("compost_spreader server started")
        await self.server.wait_for_termination()

    async def addTwoInts(
        self, request: two_ints_pb2.AddTwoIntsRequest, _: grpc.aio.ServicerContext
    ) -> two_ints_pb2.AddTwoIntsResponse:
        logger.info(f"Received request {request}")
        return two_ints_pb2.AddTwoIntsResponse(sum=request.a + request.b)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="add-two-ints-service")
    parser.add_argument("--port", type=int, default=50050, help="The service port port.")
    args = parser.parse_args()

    server = grpc.aio.server()
    service_grpc = AddTwoIntsServiceGrpc(server, port=args.port)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(service_grpc.serve())
