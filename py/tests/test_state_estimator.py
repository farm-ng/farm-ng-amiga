import pytest
from farm_ng.state_estimator import state_estimator_pb2
from farm_ng.state_estimator.state_estimator_client import StateEstimatorClient
from farm_ng.state_estimator.state_estimator_client import StateEstimatorClientConfig
from farm_ng.state_estimator.state_estimator_client import StateEstimatorServiceState


class TestStateEstimatorPb2:
    def test_smoke(self) -> None:
        request = state_estimator_pb2.RobotDynamicsRequest()
        print(request)


@pytest.fixture(name="config")
def fixture_config() -> StateEstimatorClientConfig:
    return StateEstimatorClientConfig(port=50051)


class TestStateEstimatorClient:
    def test_smoke_config(self, config: StateEstimatorClientConfig) -> None:
        assert config.port == 50051
        assert config.address == "localhost"

    def test_smoke(self, config: StateEstimatorClientConfig) -> None:
        client = StateEstimatorClient(config)
        assert client is not None
        assert client.server_address == "localhost:50051"

    @pytest.mark.asyncio
    async def test_state(self, config: StateEstimatorClientConfig) -> None:
        client = StateEstimatorClient(config)
        state: StateEstimatorServiceState = await client.get_state()
        assert state.value == state_estimator_pb2.StateEstimatorServiceState.UNAVAILABLE
