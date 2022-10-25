import pytest
from farm_ng.controller import controller_pb2
from farm_ng.controller.controller_client import ControllerClient
from farm_ng.controller.controller_client import ControllerClientConfig


class TestControllerPb2:
    def test_smoke(self) -> None:
        request = controller_pb2.MoveToGoalPoseRequest()
        print(request)


@pytest.fixture(name="config")
def fixture_config() -> ControllerClientConfig:
    return ControllerClientConfig(port=50051)


class TestControllerClient:
    def test_smoke_config(self, config: ControllerClientConfig) -> None:
        assert config.port == 50051
        assert config.address == "localhost"

    def test_smoke(self, config: ControllerClientConfig) -> None:
        client = ControllerClient(config)
        assert client is not None
        assert client.server_address == "localhost:50051"

    @pytest.mark.asyncio
    async def test_state(self, config: ControllerClientConfig) -> None:
        client = ControllerClient(config)
        state: controller_pb2.ControllerServiceState = await client.get_state()
        assert state == controller_pb2.ControllerServiceState.STOPPED
