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
import logging
from dataclasses import dataclass

import grpc
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus import canbus_pb2_grpc
from farm_ng.service import service_pb2
from farm_ng.service.service import ServiceState

logging.basicConfig(level=logging.INFO)


@dataclass
class CanbusClientConfig:
    """Canbus client configuration.

    Attributes:
        port (int): the port to connect to the server.
        address (str): the address to connect to the server.
    """

    port: int  # the port of the server address
    address: str = "localhost"  # the address name of the server


class CanbusClient:
    def __init__(self, config: CanbusClientConfig) -> None:
        self.config = config

        self.logger = logging.getLogger(self.__class__.__name__)

        # create a async connection with the server
        self.channel = grpc.aio.insecure_channel(self.server_address)
        self.stub = canbus_pb2_grpc.CanbusServiceStub(self.channel)

    @property
    def server_address(self) -> str:
        """Returns the composed address and port."""
        return f"{self.config.address}:{self.config.port}"

    async def get_state(self) -> ServiceState:
        state: ServiceState
        try:
            response: service_pb2.GetServiceStateReply = await self.stub.getServiceState(
                service_pb2.GetServiceStateRequest()
            )
            state = ServiceState(response.state)
        except grpc.RpcError:
            state = ServiceState()
        self.logger.debug("CanbusServiceStub: port -> %i state is: %s", self.config.port, state.name)
        return state

    def stream(self):
        """Return the async streaming object."""
        return self.stub.streamCanbusMessages(canbus_pb2.StreamCanbusRequest())
