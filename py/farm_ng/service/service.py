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
from farm_ng.service import service_pb2


class ServiceState:
    """Generic service state.

    Possible state values:
        - UNKNOWN: undefined state.
        - STOPPED: the service is stopped
        - RUNNING: the service is up AND streaming.
        - IDLE: the service is up AND NOT streaming.
        - UNAVAILABLE: the service is not available.
        - ERROR: the service is an error state.

    Args:
        proto (service_pb2.ServiceState): protobuf message containing the service state.
    """

    def __init__(self, proto: service_pb2.ServiceState = None) -> None:
        self._proto = service_pb2.ServiceState.UNAVAILABLE
        if proto is not None:
            self._proto = proto

    @property
    def value(self) -> int:
        """Returns the state enum value."""
        return self._proto

    @property
    def name(self) -> str:
        """Return the state name."""
        return service_pb2.ServiceState.DESCRIPTOR.values[self.value].name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: ({self.value}, {self.name})"
