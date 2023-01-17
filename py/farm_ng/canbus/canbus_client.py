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

from farm_ng.canbus import canbus_pb2
from farm_ng.canbus import canbus_pb2_grpc
from farm_ng.service.service_client import ClientConfig
from farm_ng.service.service_client import ServiceClient

logging.basicConfig(level=logging.INFO)


class CanbusClient(ServiceClient):
    """Amiga canbus client.

    Client class to connect with the Amiga brain canbus service.
    Inherits from ServiceClient.

    Args:
        config (ClientConfig): the grpc configuration data structure.
    """

    def __init__(self, config: ClientConfig) -> None:
        super().__init__(config)
        # create a async connection with the server
        self.stub = canbus_pb2_grpc.CanbusServiceStub(self.channel)

    def stream(self):
        """Return the async streaming object."""
        return self.stub.streamCanbusMessages(canbus_pb2.StreamCanbusRequest())
