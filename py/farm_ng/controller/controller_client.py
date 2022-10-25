import asyncio
import logging
from dataclasses import dataclass

import grpc
from farm_ng.controller import controller_pb2
from farm_ng.controller import controller_pb2_grpc

logging.basicConfig(level=logging.DEBUG)


@dataclass
class ControllerClientConfig:
    """Controller client configuration.

    Attributes:
        port (int): the port to connect to the server.
        address (str): the address to connect to the server.
    """

    port: int  # the port of the server address
    address: str = "localhost"  # the address name of the server


class ControllerClient:
    def __init__(self, config: ControllerClientConfig) -> None:
        self.config = config

        self.logger = logging.getLogger(self.__class__.__name__)

        # create a async connection with the server
        self.channel = grpc.aio.insecure_channel(self.server_address)
        self.stub = controller_pb2_grpc.ControllerServiceStub(self.channel)

        self._state = controller_pb2.ControllerServiceState.STOPPED

    @property
    def state(self) -> controller_pb2.ControllerServiceState:
        return self._state

    @property
    def server_address(self) -> str:
        """Returns the composed address and port."""
        return f"{self.config.address}:{self.config.port}"

    async def _poll_service_state(self) -> None:
        while True:
            try:
                self._state = await self.get_state()
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                self.logger.info("Got Cancelled Error")
                break

    async def get_state(self) -> controller_pb2.ControllerServiceState:
        state: controller_pb2.ControllerServiceState
        try:
            response: controller_pb2.GetServiceStateResult = await self.stub.getServiceState(
                controller_pb2.GetServiceStateRequest()
            )
            state = response.state
        except grpc.RpcError:
            state = controller_pb2.ControllerServiceState.STOPPED
        self.logger.debug("ControllerServiceStub: port -> %i state is: %s", self.config.port, state)
        return state

    async def start_service(self) -> None:
        state: controller_pb2.ControllerServiceState = await self.get_state()
        if state.value == controller_pb2.ServiceState.STOPPED:
            return
        await self.stub.startService(controller_pb2.StartServiceRequest())

    async def stop_service(self) -> None:
        state: controller_pb2.ControllerServiceState = await self.get_state()
        if state.value == controller_pb2.ControllerServiceState.STOPPED:
            return
        await self.stub.stopService(controller_pb2.StopServiceRequest())

    # def move_to_goal(self):
    #     """Return the async streaming object.
    #     Args:
    #         None
    #     """
    #     return self.stub.moveToGoalPose(controller_pb2.MoveToGoalPoseRequest())
