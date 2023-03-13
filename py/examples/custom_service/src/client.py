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

import two_ints_pb2
import two_ints_pb2_grpc
from farm_ng.service.service_client import ClientConfig
from farm_ng.service.service_client import ServiceClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AddTwoIntsClient(ServiceClient):
    def __init__(self, config: ClientConfig) -> None:
        super().__init__(config)

        self.stub = two_ints_pb2_grpc.AddTwoIntsServiceStub(self.channel)

    async def add_two_ints(self, a: int, b: int) -> int:
        response: two_ints_pb2.AddTwoIntsResponse = await self.stub.addTwoInts(two_ints_pb2.AddTwoIntsRequest(a=a, b=b))
        return response.sum


async def main(config: ClientConfig, a: int, b: int) -> None:
    # create an instance of the client
    client = AddTwoIntsClient(config)

    # call the service method
    sum_value: int = await client.add_two_ints(a, b)

    # print the result
    logger.info(f"The result of {a} + {b} = {sum_value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="compost-spreader-client")
    parser.add_argument("--host", type=str, default="localhost", help="The server host address.")
    parser.add_argument("--port", type=int, default=50050, help="The server port.")
    parser.add_argument("--a", type=int, required=True, help="The first integer to add.")
    parser.add_argument("--b", type=int, required=True, help="The second integer to add.")
    args = parser.parse_args()

    client_config = ClientConfig(address=args.host, port=args.port)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(client_config, args.a, args.b))
