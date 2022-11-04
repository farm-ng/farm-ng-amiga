# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
import asyncio
import logging
import time
from dataclasses import dataclass

import grpc
from farm_ng.oak import oak_pb2
from farm_ng.oak import oak_pb2_grpc

__all__ = ["OakCameraClientConfig", "OakCameraClient", "OakCameraServiceState"]

logging.basicConfig(level=logging.INFO)


class RateLimiter:
    def __init__(self, period):
        self.last_call = None
        self.period = period
        self.outstanding_call = False
        self.args = None
        self.kargs = None

    def wrapper(self, func):
        self.last_call = time.monotonic()
        self.outstanding_call = False
        func(*self.args, **self.kargs)

    def __call__(self, func):
        """Return a wrapped function that can only be called once per frequency where the most recent call will be
        executed."""

        def async_wrapper(*args, **kargs):
            self.args = args
            self.kargs = kargs
            delay = self.next_call_wait()
            if delay < 0:
                self.wrapper(func)
            else:
                if not self.outstanding_call:
                    asyncio.get_running_loop().call_later(delay, self.wrapper, func)
                    self.outstanding_call = True

        return async_wrapper

    def next_call_wait(self):
        if self.last_call is None:
            return -1
        return self.period - (time.monotonic() - self.last_call)


@dataclass
class OakCameraClientConfig:
    """Camera client configuration.

    Attributes:
        port (int): the port to connect to the server.
        address (str): the address to connect to the server.
    """

    port: int  # the port of the server address
    address: str = "localhost"  # the address name of the server


class OakCameraServiceState:
    """Camera service state.

    Possible state values:
        - UNKNOWN: undefined state.
        - RUNNING: the service is up AND streaming.
        - IDLE: the service is up AND NOT streaming.
        - UNAVAILABLE: the service is not available.

    Args:
        proto (oak_pb2.OakServiceState): protobuf message containing the camera state.
    """

    def __init__(self, proto: oak_pb2.OakServiceState = None) -> None:
        self._proto = proto or oak_pb2.OakServiceState.UNAVAILABLE

    @property
    def value(self) -> int:
        """Returns the state enum value."""
        return self._proto

    @property
    def name(self) -> str:
        """Return the state name."""
        return oak_pb2.OakServiceState.DESCRIPTOR.values[self.value].name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: ({self.value}, {self.name})"


class OakCameraClient:
    """Oak-D camera client.

    Client class to connect with the Amiga brain camera services.
    Internally implements an `asyncio` gRPC channel.

    Args:
        config (OakCameraClientConfig): the camera configuration data structure.
    """

    def __init__(self, config: OakCameraClientConfig) -> None:
        self.config = config

        self.logger = logging.getLogger(self.__class__.__name__)

        # create a async connection with the server
        self.channel = grpc.aio.insecure_channel(self.server_address)
        self.stub = oak_pb2_grpc.OakServiceStub(self.channel)

        self._state = OakCameraServiceState()

        self._mono_camera_settings = oak_pb2.CameraSettings(auto_exposure=True)
        self._rgb_camera_settings = oak_pb2.CameraSettings(auto_exposure=True)

        self.needs_update = False

    @property
    def state(self) -> OakCameraServiceState:
        return self._state

    @property
    def server_address(self) -> str:
        """Returns the composed address and port."""
        return f"{self.config.address}:{self.config.port}"

    @property
    def rgb_settings(self) -> str:
        return self._rgb_camera_settings

    @property
    def mono_settings(self) -> str:
        return self._mono_camera_settings

    def settings_reply(self, reply) -> None:
        if reply.status == oak_pb2.ReplyStatus.OK:
            self._mono_camera_settings.CopyFrom(reply.stereo_settings)
            self._rgb_camera_settings.CopyFrom(reply.rgb_settings)

    async def poll_service_state(self) -> None:
        while True:
            try:
                self._state = await self.get_state()
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                self.logger.info("Got CancellededError")
                break

    async def get_state(self) -> OakCameraServiceState:
        """Async call to retrieve the state of the connected service."""
        state: OakCameraServiceState
        try:
            response: oak_pb2.GetServiceStateResponse = await self.stub.getServiceState(
                oak_pb2.GetServiceStateRequest()
            )
            state = OakCameraServiceState(response.state)
        except grpc.RpcError:
            state = OakCameraServiceState()
        self.logger.debug("OakServiceStub: port -> %i state is: %s", self.config.port, state.name)
        return state

    async def connect_to_service(self) -> None:
        """Start the camera streaming.

        The service state will go from `IDLE` to `RUNNING`.
        """
        state: OakCameraServiceState = await self.get_state()
        if state.value == oak_pb2.OakServiceState.UNAVAILABLE:
            return
        reply = await self.stub.cameraControl(oak_pb2.CameraControlRequest())
        self.settings_reply(reply)
        await self.stub.startService(oak_pb2.StartServiceRequest())

    async def pause_service(self) -> None:
        """Pauses the camera streaming.

        The service state will go from `RUNNING` to `IDLE`.
        """
        state: OakCameraServiceState = await self.get_state()
        if state.value == oak_pb2.OakServiceState.UNAVAILABLE:
            return
        await self.stub.pauseService(oak_pb2.PauseServiceRequest())

    async def send_settings(self) -> oak_pb2.CameraControlReply:
        request = oak_pb2.CameraControlRequest()
        request.stereo_settings.CopyFrom(self._mono_camera_settings)
        request.rgb_settings.CopyFrom(self._rgb_camera_settings)
        self.needs_update = False
        return await self.stub.cameraControl(request)

    @RateLimiter(period=1)
    def update_rgb_settings(self, rgb_settings):
        self.needs_update = True
        self._rgb_camera_settings = rgb_settings

    @RateLimiter(period=1)
    def update_mono_settings(self, mono_settings):
        self.needs_update = True
        self._mono_camera_settings = mono_settings

    def stream_frames(self, every_n: int):
        """Return the async streaming object.

        Args:
            every_n: the streaming frequency. In practice, drops `n` frames.
        """
        return self.stub.streamFrames(oak_pb2.StreamFramesRequest(every_n=every_n))
