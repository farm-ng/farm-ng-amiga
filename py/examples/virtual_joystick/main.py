# Copyright (c) farm-ng, inc. All rights reserved.
import argparse
import asyncio
import os
from typing import List

from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.canbus.canbus_client import CanbusClientConfig

# from farm_ng.canbus import canbus_pb2
# from farm_ng.canbus.canbus_client import CanbusServiceState

os.environ["KIVY_NO_ARGS"] = "1"


from kivy.config import Config  # noreorder # noqa: E402

Config.set("graphics", "fullscreen", "false")

from kivy.app import App  # noqa: E402
from kivy.lang.builder import Builder  # noqa: E402

kv = """
TabbedPanel:
    do_default_tab: False
    TabbedPanelItem:
        text: "Rgb"
        Image:
            id: rgb
    TabbedPanelItem:
        text: "Disparity"
        Image:
            id: disparity
    TabbedPanelItem:
        text: "Left"
        Image:
            id: left
    TabbedPanelItem:
        text: "Right"
        Image:
            id: right
"""


class VirtualPendantApp(App):
    def __init__(self, address: str, port: int) -> None:
        super().__init__()
        self.address = address
        self.port = port

        self.tasks: List[asyncio.Task] = []

        self.client: CanbusClient
        self.config: CanbusClientConfig

    def build(self):
        return Builder.load_string(kv)

    async def app_func(self):
        async def run_wrapper():
            # we don't actually need to set asyncio as the lib because it is
            # the default, but it doesn't hurt to be explicit
            await self.async_run(async_lib="asyncio")
            for task in self.tasks:
                task.cancel()

        # configure the camera client
        self.config = CanbusClientConfig(address=self.address, port=self.port)
        self.client = CanbusClient(self.config)

        self.tasks.append(asyncio.ensure_future(self.stream_canbus(self.client)))

        return await asyncio.gather(run_wrapper(), *self.tasks)

    async def stream_canbus(self, client: CanbusClient) -> None:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-camera-app")
    parser.add_argument("--address", type=str, default="localhost", help="The camera address")
    parser.add_argument("--port", type=int, required=True, help="The grpc port where the canbus service is running.")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(VirtualPendantApp(args.address, args.port).app_func())
    except asyncio.CancelledError:
        pass
    loop.close()
