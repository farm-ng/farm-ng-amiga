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
import argparse
import asyncio
import io
import os
from typing import List

import grpc
from farm_ng.oak import oak_pb2
from farm_ng.oak.camera_client import OakCameraClient
from farm_ng.service import service_pb2
from farm_ng.service.service_client import ClientConfig

os.environ["KIVY_NO_ARGS"] = "1"


from kivy.config import Config  # noreorder # noqa: E402

Config.set("graphics", "fullscreen", "false")

from kivy.app import App  # noqa: E402
from kivy.lang.builder import Builder  # noqa: E402
from kivy.core.image import Image as CoreImage  # noqa: E402

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


class CameraApp(App):
    def __init__(self, address: str, port: int, stream_every_n: int) -> None:
        super().__init__()
        self.address = address
        self.port = port
        self.stream_every_n = stream_every_n

        self.tasks: List[asyncio.Task] = []

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
        config = ClientConfig(address=self.address, port=self.port)
        client = OakCameraClient(config)

        # Stream camera frames
        self.tasks.append(asyncio.ensure_future(self.stream_camera(client)))

        return await asyncio.gather(run_wrapper(), *self.tasks)

    async def stream_camera(self, client: OakCameraClient) -> None:
        """This task listens to the camera client's stream and populates the tabbed panel with all 4 image streams
        from the oak camera."""
        while self.root is None:
            await asyncio.sleep(0.01)

        response_stream = None

        while True:
            # check the state of the service
            state = await client.get_state()

            if state.value not in [service_pb2.ServiceState.IDLE, service_pb2.ServiceState.RUNNING]:
                # Cancel existing stream, if it exists
                if response_stream is not None:
                    response_stream.cancel()
                    response_stream = None
                print("Camera service is not streaming or ready to stream")
                await asyncio.sleep(0.1)
                continue

            # Create the stream
            if response_stream is None:
                response_stream = client.stream_frames(every_n=1)

            try:
                # try/except so app doesn't crash on killed service
                response: oak_pb2.StreamFramesReply = await response_stream.read()
                assert response and response != grpc.aio.EOF, "End of stream"
            except Exception as e:
                print(e)
                response_stream.cancel()
                response_stream = None
                continue

            # get the sync frame
            frame: oak_pb2.OakSyncFrame = response.frame

            # get image and show
            for view_name in ["rgb", "disparity", "left", "right"]:
                # Skip if view_name was not included in frame
                try:
                    self.root.ids[view_name].texture = CoreImage(
                        io.BytesIO(getattr(frame, view_name).image_data), ext="jpg"
                    ).texture
                except Exception as e:
                    print(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-camera-app")
    parser.add_argument("--port", type=int, required=True, help="The camera port.")
    parser.add_argument("--address", type=str, default="localhost", help="The camera address")
    parser.add_argument("--stream-every-n", type=int, default=4, help="Streaming frequency")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(CameraApp(args.address, args.port, args.stream_every_n).app_func())
    except asyncio.CancelledError:
        pass
    loop.close()
