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

from farm_ng.gps import gps_pb2
from farm_ng.gps import gps_pb2_grpc
from farm_ng.service.service_client import ClientConfig
from farm_ng.service.service_client import ServiceClient

logging.basicConfig(level=logging.INFO)


class GpsClient(ServiceClient):
    """Amiga GPS client.

    Client class to connect with the Amiga brain GPS service.
    Inherits from ServiceClient.
    Args:
        config (ClientConfig): the grpc configuration data structure.
    """

    def __init__(self, config: ClientConfig) -> None:
        super().__init__(config)
        # create a async connection with the server
        self.stub = gps_pb2_grpc.GpsServiceStub(self.channel)

    def stream_gps(self):
        """Return the async streaming object of GPS frame messages."""
        return self.stub.streamFrames(gps_pb2.StreamFramesRequest())

    def stream_relative_position(self):
        """Return the async streaming object of GPS relative frame messages."""
        return self.stub.streamRelativePositionFrames(gps_pb2.StreamRelPositionRequest())