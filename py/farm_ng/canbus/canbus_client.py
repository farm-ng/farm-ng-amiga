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


class CanbusServiceState:
    """Canbus service state."""

    def __init__(self, proto: canbus_pb2.CanbusServiceState = None) -> None:
        self._proto = canbus_pb2.CanbusServiceState.UNAVAILABLE
        if proto is not None:
            self._proto = proto

    @property
    def value(self) -> int:
        return self._proto

    @property
    def name(self) -> str:
        return canbus_pb2.CanbusServiceState.DESCRIPTOR.values[self.value].name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: ({self.value}, {self.name})"


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

    async def get_state(self) -> CanbusServiceState:
        state: CanbusServiceState
        try:
            response: canbus_pb2.GetServiceStateResponse = await self.stub.getServiceState(
                canbus_pb2.GetServiceStateRequest()
            )
            state = CanbusServiceState(response.state)
        except grpc.RpcError:
            state = CanbusServiceState()
        self.logger.debug("CanbusServiceStub: port -> %i state is: %s", self.config.port, state.name)
        return state
