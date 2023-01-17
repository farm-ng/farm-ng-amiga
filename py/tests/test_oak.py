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
import pytest
from farm_ng.oak.camera_client import OakCameraClient
from farm_ng.service import service_pb2
from farm_ng.service.service_client import ClientConfig
from farm_ng.service.service_client import ServiceState


@pytest.fixture(name="config")
def fixture_config() -> ClientConfig:
    return ClientConfig(port=50051)


class TestOakClient:
    def test_smoke_config(self, config: ClientConfig) -> None:
        assert config.port == 50051
        assert config.address == "localhost"

    def test_smoke(self, config: ClientConfig) -> None:
        client = OakCameraClient(config)
        assert client is not None
        assert client.server_address == "localhost:50051"

    @pytest.mark.asyncio
    async def test_state(self, config: ClientConfig) -> None:
        client = OakCameraClient(config)
        state: ServiceState = await client.get_state()
        assert state.value == service_pb2.ServiceState.UNAVAILABLE
