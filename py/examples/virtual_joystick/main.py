# Copyright (c) farm-ng, inc. All rights reserved.
import argparse
import asyncio
import io
import logging
import os
from typing import List
from typing import Optional
from typing import Tuple

import grpc
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.canbus.canbus_client import CanbusClientConfig
from farm_ng.canbus.packet import AmigaControlState
from farm_ng.canbus.packet import AmigaRpdo1
from farm_ng.canbus.packet import AmigaTpdo1
from farm_ng.canbus.packet import DASHBOARD_NODE_ID
from farm_ng.oak import oak_pb2
from farm_ng.oak.camera_client import OakCameraClient
from farm_ng.oak.camera_client import OakCameraClientConfig

# Must come before kivy imports
os.environ["KIVY_NO_ARGS"] = "1"

from kivy.config import Config  # noreorder # noqa: E402
from kivy.graphics import Color, Ellipse  # noqa: E402
from kivy.input.providers.mouse import MouseMotionEvent  # noqa: E402
from kivy.properties import StringProperty  # noqa: E402

Config.set("graphics", "resizable", False)
Config.set("graphics", "width", "1280")
Config.set("graphics", "height", "800")
Config.set("graphics", "fullscreen", "false")
Config.set("input", "mouse", "mouse,disable_on_activity")
Config.set("kivy", "keyboard_mode", "systemanddock")

from kivy.app import App  # noqa: E402
from kivy.lang.builder import Builder  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402
from kivy.core.image import Image as CoreImage  # noqa: E402


kv = """
<VirtualJoystickWidget@Widget>:
BoxLayout:
    BoxLayout:
        size_hint_x: 0.3
        orientation: 'vertical'
        Label:
            text: "state:\\n" + str(app.amiga_state)
        Label:
            text: "speed:\\n" + str(app.amiga_speed) + " [m/s]"
        Label:
            text: "angular rate:\\n" + str(app.amiga_rate) + " [rad/s]"
    VirtualJoystickWidget:
        id: joystick
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


class VirtualJoystickWidget(Widget):
    def __init__(self, **kwargs) -> None:
        super(VirtualJoystickWidget, self).__init__(**kwargs)

        self.pose: tuple[float, float] = (0.0, 0.0)
        self.joystick_rad = 100

    @staticmethod
    def relative_cord_in_widget(
        widget: Widget, touch: MouseMotionEvent, scale: Tuple[float, float] = (-1.0, 1.0), buffer: float = 0
    ) -> Optional[Tuple[float, float]]:
        """Returns the coordinates of the touch on the scale IFF it occurs within the bounds of the widget (plus
        the buffer).

        The buffer is useful to draw a complete shape within the bounds
        """
        xs = (widget.pos[0] + buffer, widget.pos[0] + widget.width - buffer)
        ys = (widget.pos[1] + buffer, widget.pos[1] + widget.height - buffer)
        if not (xs[0] < touch.x < xs[1]) or not (ys[0] < touch.y < ys[1]):
            return None

        return (
            scale[0] + (touch.x - xs[0]) * (scale[1] - scale[0]) / (widget.width - 2 * buffer),
            scale[0] + (touch.y - ys[0]) * (scale[1] - scale[0]) / (widget.height - 2 * buffer),
        )

    def on_touch_down(self, touch):
        if isinstance(touch, MouseMotionEvent) and int(os.environ.get("DISABLE_KIVY_MOUSE_EVENTS", 0)):
            return True
        for w in self.children[:]:
            if w.dispatch("on_touch_down", touch):
                return True
        #
        res = self.relative_cord_in_widget(widget=self, touch=touch, buffer=self.joystick_rad)
        if res:
            self.pose = res
        return False

    def on_touch_move(self, touch):
        if isinstance(touch, MouseMotionEvent) and int(os.environ.get("DISABLE_KIVY_MOUSE_EVENTS", 0)):
            return True
        for w in self.children[:]:
            if w.dispatch("on_touch_move", touch):
                return True

        res = self.relative_cord_in_widget(widget=self, touch=touch, buffer=self.joystick_rad)
        if res:
            self.pose = res
        return False

    def on_touch_up(self, touch):
        if isinstance(touch, MouseMotionEvent) and int(os.environ.get("DISABLE_KIVY_MOUSE_EVENTS", 0)):
            return True
        for w in self.children[:]:
            if w.dispatch("on_touch_up", touch):
                return True

        self.pose = (0.0, 0.0)
        return False

    def draw(self):
        self.canvas.clear()

        x_abs, y_abs = (
            self.center_x + 0.5 * self.pose[0] * (self.width - 2 * self.joystick_rad),
            self.center_y + 0.5 * self.pose[1] * (self.height - 2 * self.joystick_rad),
        )
        self.canvas.add(Color(1.0, 1.0, 0.0, 1.0, mode="rgba"))
        point_obj = Ellipse(
            pos=(x_abs - self.joystick_rad, y_abs - self.joystick_rad),
            size=(self.joystick_rad * 2, self.joystick_rad * 2),
        )
        self.canvas.add(point_obj)


class VirtualPendantApp(App):
    # For kivy labels
    amiga_speed = StringProperty()
    amiga_rate = StringProperty()
    amiga_state = StringProperty()

    def __init__(self, address: str, camera_port: int, canbus_port: int, stream_every_n: int) -> None:
        super().__init__()
        self.address = address
        self.camera_port = camera_port
        self.canbus_port = canbus_port
        self.stream_every_n = stream_every_n

        self.tasks: List[asyncio.Task] = []

        # Received
        self.amiga_tpdo1 = AmigaTpdo1()
        self.amiga_state = "NO CANBUS\nSERVICE DETECTED"
        self.amiga_speed = "???"
        self.amiga_rate = "???"

        self.max_speed = 1.0
        self.max_angular_rate = 1.0

        self.canbus_client: CanbusClient
        self.canbus_config: CanbusClientConfig

        self.camera_client: OakCameraClient
        self.camera_config: OakCameraClientConfig

    def build(self):
        return Builder.load_string(kv)

    def update_kivy_strings(self):
        self.amiga_state = AmigaControlState(self.amiga_tpdo1.state).name
        self.amiga_speed = str(self.amiga_tpdo1.meas_speed)
        self.amiga_rate = str(self.amiga_tpdo1.meas_ang_rate)

    async def draw_joystick(self):
        """Loop over drawing the VirtualJoystickWidget."""
        while self.root is None:
            await asyncio.sleep(0.01)
        joystick = self.root.ids["joystick"]
        while True:
            joystick.draw()
            await asyncio.sleep(0.01)

    async def app_func(self):
        async def run_wrapper():
            # we don't actually need to set asyncio as the lib because it is
            # the default, but it doesn't hurt to be explicit
            await self.async_run(async_lib="asyncio")
            for task in self.tasks:
                task.cancel()

        # configure the canbus client
        self.canbus_config = CanbusClientConfig(address=self.address, port=self.canbus_port)
        self.canbus_client = CanbusClient(self.canbus_config)

        # configure the camera client
        self.camera_config = OakCameraClientConfig(address=self.address, port=self.camera_port)
        self.camera_client = OakCameraClient(self.camera_config)

        # Drawing task(s)
        self.tasks.append(asyncio.ensure_future(self.draw_joystick()))

        # Canbus task(s)
        self.tasks.append(asyncio.ensure_future(self.stream_canbus(self.canbus_client)))
        self.tasks.append(asyncio.ensure_future(self.send_can_msgs(self.canbus_client)))
        self.tasks.append(asyncio.ensure_future(self.canbus_client.poll_service_state()))

        # Camera task(s)
        self.tasks.append(asyncio.ensure_future(self.stream_camera(self.camera_client)))
        self.tasks.append(asyncio.ensure_future(self.camera_client.poll_service_state()))

        return await asyncio.gather(run_wrapper(), *self.tasks)

    async def stream_camera(self, client: OakCameraClient) -> None:
        """This task listens to the camera client's stream and populates
        the tabbed panel with all 4 image streams from the oak camera
        """
        while self.root is None:
            await asyncio.sleep(0.01)

        response_stream = None

        while True:
            if client.state.value != oak_pb2.OakServiceState.RUNNING:
                # start the streaming service
                await client.start_service()
                await asyncio.sleep(0.01)
                continue
            elif response_stream is None:
                # get the streaming object
                response_stream = client.stream_frames(every_n=self.stream_every_n)
                await asyncio.sleep(0.01)
                continue

            response: oak_pb2.StreamFramesReply = await response_stream.read()
            if response and response.status == oak_pb2.ReplyStatus.OK:
                # get the sync frame
                frame: oak_pb2.OakSyncFrame = response.frame

                # get image and show
                for view_name in ["rgb", "disparity", "left", "right"]:
                    self.root.ids[view_name].texture = CoreImage(
                        io.BytesIO(getattr(frame, view_name).image_data), ext="jpg"
                    ).texture

    async def send_can_msgs(self, client: CanbusClient) -> None:
        """This task ensures the canbus client sendCanbusMessage method has the pose_generator it will use to send
        messages on the can bus."""
        while self.root is None:
            await asyncio.sleep(0.01)

        while True:
            if client.state.value != canbus_pb2.CanbusServiceState.RUNNING:
                logging.debug("Controller requires running canbus service")
                client.stub.sendCanbusMessage(self.pose_generator())
            await asyncio.sleep(0.25)

    async def pose_generator(self, period: float = 0.02):
        """The pose generator yields an AmigaAmigaRpdo1 (auto control command) for the canbus client to send on the
        bus at the specified period (recommended 50hz) based on the onscreen joystick position."""
        assert self.root is not None, ""
        joystick = self.root.ids["joystick"]

        while True:
            rpdo1 = AmigaRpdo1(
                state_req=AmigaControlState.STATE_AUTO_ACTIVE,
                cmd_speed=self.max_speed * joystick.pose[1],
                cmd_ang_rate=self.max_angular_rate * -joystick.pose[0],
            )
            msg = canbus_pb2.RawCanbusMessage(id=rpdo1.cob_id + DASHBOARD_NODE_ID, data=rpdo1.encode())
            yield canbus_pb2.SendCanbusMessageRequest(message=msg)
            await asyncio.sleep(period)

    async def stream_canbus(self, client: CanbusClient) -> None:
        """This task:

        - listens to the canbus client's stream
        - filters for AmigaTpdo1 messages
        - extracts useful values from AmigaTpdo1 messages
        """
        response_stream = None

        while True:
            if client.state.value == canbus_pb2.CanbusServiceState.UNAVAILABLE:
                await asyncio.sleep(0.01)
                continue
            if response_stream is None:
                response_stream = client.stub.streamCanbusMessages(canbus_pb2.StreamCanbusRequest())
                await asyncio.sleep(0.01)
                continue

            response: canbus_pb2.StreamCanbusReply = await response_stream.read()
            if response == grpc.aio.EOF:
                break
            if response and response.status == canbus_pb2.ReplyStatus.OK:
                for proto in response.messages.messages:
                    if proto.id == AmigaTpdo1.cob_id + DASHBOARD_NODE_ID:
                        self.amiga_tpdo1 = AmigaTpdo1.from_can_data(proto.data)
                        self.update_kivy_strings()
            await asyncio.sleep(0.001)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="virtual-joystick")
    parser.add_argument("--address", type=str, default="localhost", help="The camera address")
    parser.add_argument(
        "--camera-port", type=int, required=True, help="The grpc port where the camera service is running."
    )
    parser.add_argument(
        "--canbus-port", type=int, required=True, help="The grpc port where the canbus service is running."
    )
    parser.add_argument("--stream-every-n", type=int, default=1, help="Streaming frequency (used to skip frames)")

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            VirtualPendantApp(args.address, args.camera_port, args.canbus_port, args.stream_every_n).app_func()
        )
    except asyncio.CancelledError:
        pass
    loop.close()
