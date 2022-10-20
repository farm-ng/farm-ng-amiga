import pytest
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.canbus.canbus_client import CanbusClientConfig
from farm_ng.canbus.canbus_client import CanbusServiceState


@pytest.fixture(name="config")
def fixture_config() -> CanbusClientConfig:
    return CanbusClientConfig(port=50051)


class TestCanbusClient:
    def test_smoke_config(self, config: CanbusClientConfig) -> None:
        assert config.port == 50051
        assert config.address == "localhost"

    def test_smoke(self, config: CanbusClientConfig) -> None:
        client = CanbusClient(config)
        assert client is not None
        assert client.server_address == "localhost:50051"

    @pytest.mark.asyncio
    async def test_state(self, config: CanbusClientConfig) -> None:
        client = CanbusClient(config)
        state: CanbusServiceState = await client.get_state()
        assert state.value == canbus_pb2.CanbusServiceState.STOPPED
