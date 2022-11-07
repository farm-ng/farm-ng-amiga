# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
import asyncio
import logging
from dataclasses import dataclass

import grpc
from farm_ng.state_estimator import state_estimator_pb2
from farm_ng.state_estimator import state_estimator_pb2_grpc

logging.basicConfig(level=logging.DEBUG)


@dataclass
class StateEstimatorClientConfig:
    """StateEstimator client configuration.

    Attributes:
        port (int): the port to connect to the server.
        address (str): the address to connect to the server.
    """

    port: int  # the port of the server address
    address: str = "localhost"  # the address name of the server


class StateEstimatorServiceState:
    """State estimator service state."""

    def __init__(self, proto: state_estimator_pb2.StateEstimatorServiceState = None) -> None:
        self._proto = proto or state_estimator_pb2.StateEstimatorServiceState.UNAVAILABLE

    @property
    def value(self) -> int:
        return self._proto

    @property
    def name(self) -> str:
        return state_estimator_pb2.StateEstimatorServiceState.DESCRIPTOR.values[self.value].name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: ({self.value}, {self.name})"


class StateEstimatorClient:
    def __init__(self, config: StateEstimatorClientConfig) -> None:
        self.config = config

        self.logger = logging.getLogger(self.__class__.__name__)

        # create a async connection with the server
        self.channel = grpc.aio.insecure_channel(self.server_address)
        self.stub = state_estimator_pb2_grpc.StateEstimatorServiceStub(self.channel)

        self._state = StateEstimatorServiceState()

    @property
    def state(self) -> StateEstimatorServiceState:
        return self._state

    @property
    def server_address(self) -> str:
        """Returns the composed address and port."""
        return f"{self.config.address}:{self.config.port}"

    async def poll_service_state(self) -> None:
        while True:
            try:
                self._state = await self.get_state()
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                self.logger.info("Got Cancelled Error")
                break

    async def get_state(self) -> StateEstimatorServiceState:
        state: StateEstimatorServiceState
        try:
            response: state_estimator_pb2.GetServiceStateResult = await self.stub.getServiceState(
                state_estimator_pb2.GetServiceStateRequest()
            )
            state = StateEstimatorServiceState(response.state)
        except grpc.RpcError:
            state = StateEstimatorServiceState()
        self.logger.debug("StateEstimatorServiceStub: port -> %i state is: %s", self.config.port, state)
        return state

    async def connect_to_service(self) -> None:
        state: StateEstimatorServiceState = await self.get_state()
        if state.value == state_estimator_pb2.StateEstimatorServiceState.UNAVAILABLE:
            return
        await self.stub.startService(state_estimator_pb2.StartServiceRequest())

    async def disconnect_from_service(self) -> None:
        state: StateEstimatorServiceState = await self.get_state()
        if state.value == state_estimator_pb2.StateEstimatorServiceState.UNAVAILABLE:
            return
        await self.stub.stopService(state_estimator_pb2.StopServiceRequest())
