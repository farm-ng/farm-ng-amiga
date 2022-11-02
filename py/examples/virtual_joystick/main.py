# Copyright (c) farm-ng, inc. All rights reserved.
import argparse
import asyncio
import logging
import os
from typing import List

import grpc
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.canbus.canbus_client import CanbusClientConfig
from farm_ng.canbus.packet import AmigaControlState
from farm_ng.canbus.packet import AmigaRpdo1
from farm_ng.canbus.packet import AmigaTpdo1
from farm_ng.canbus.packet import DASHBOARD_NODE_ID

# Must come before kivy imports
os.environ["KIVY_NO_ARGS"] = "1"

from kivy.config import Config  # noreorder # noqa: E402
from kivy.graphics import Color, Ellipse  # noqa: E402
from kivy.input.providers.mouse import MouseMotionEvent  # noqa: E402
from kivy.properties import StringProperty  # noqa: E402

Config.set("graphics", "fullscreen", "false")

from kivy.app import App  # noqa: E402
from kivy.lang.builder import Builder  # noqa: E402
from kivy.core.window import Window  # noqa: E402


kv = """
# <VirtualJoystickWidget@Widget>:
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
    Widget:
        id: joystick
"""


class VirtualPendantApp(App):
    # For kivy labels
    amiga_speed = StringProperty()
    amiga_rate = StringProperty()
    amiga_state = StringProperty()

    def __init__(self, address: str, port: int) -> None:
        super().__init__()
        self.address = address
        self.port = port

        self.tasks: List[asyncio.Task] = []

        # Received
        self.amiga_tpdo1 = AmigaTpdo1()
        self.amiga_state = "NO CANBUS\nSERVICE DETECTED"
        self.amiga_speed = "???"
        self.amiga_rate = "???"
        self.app = App.get_running_app()

        self.joystick_pose: tuple[float, float] = (0.0, 0.0)
        self.max_speed = 1.0
        self.max_angular_rate = 1.0

        self.client: CanbusClient
        self.config: CanbusClientConfig

    def build(self):
        def on_touch_down(window: Window, touch):
            if isinstance(touch, MouseMotionEvent) and int(os.environ.get("DISABLE_KIVY_MOUSE_EVENTS", 0)):
                return True
            for w in window.children[:]:
                if w.dispatch("on_touch_down", touch):
                    return True

            self.joystick_pose = (-1.0 + 2.0 * (touch.sx - 0.3) / 0.7, -1.0 + 2.0 * touch.sy)
            self.joystick_pose = (min(max(-1, self.joystick_pose[0]), 1), min(max(-1, self.joystick_pose[1]), 1))
            return False

        def on_touch_move(window: Window, touch):

            if isinstance(touch, MouseMotionEvent) and int(os.environ.get("DISABLE_KIVY_MOUSE_EVENTS", 0)):
                return True
            for w in window.children[:]:
                if w.dispatch("on_touch_move", touch):
                    return True

            self.joystick_pose = (1.0 - 2.0 * (touch.sx - 0.3) / 0.7, -1.0 + 2.0 * touch.sy)
            self.joystick_pose = (min(max(-1, self.joystick_pose[0]), 1), min(max(-1, self.joystick_pose[1]), 1))

            return False

        def on_touch_up(window: Window, touch):
            if isinstance(touch, MouseMotionEvent) and int(os.environ.get("DISABLE_KIVY_MOUSE_EVENTS", 0)):
                return True
            for w in window.children[:]:
                if w.dispatch("on_touch_up", touch):
                    return True

            self.joystick_pose = (0.0, 0.0)
            return False

        Window.bind(on_touch_down=on_touch_down)
        Window.bind(on_touch_move=on_touch_move)
        Window.bind(on_touch_up=on_touch_up)
        return Builder.load_string(kv)

    def update_kivy_strings(self):
        self.amiga_state = AmigaControlState(self.amiga_tpdo1.state).name
        self.amiga_speed = str(self.amiga_tpdo1.meas_speed)
        self.amiga_rate = str(self.amiga_tpdo1.meas_ang_rate)

    async def draw_joystick(self):
        while self.root is None:
            await asyncio.sleep(0.01)
            widget = self.app.root.ids["joystick"]
        while True:
            widget.canvas.clear()
            size = (100, 100)
            widget.canvas.add(Color(1.0, 1.0, 0.0, 1.0, mode="rgba"))
            x_abs, y_abs = (
                widget.center_x - 0.5 * self.joystick_pose[0] * widget.width,
                widget.center_y + 0.5 * self.joystick_pose[1] * widget.height,
            )
            point_obj = Ellipse(pos=(x_abs - size[0] // 2, y_abs - size[1] // 2), size=size)
            widget.canvas.add(point_obj)

            await asyncio.sleep(0.01)

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

        self.tasks.append(asyncio.ensure_future(self.draw_joystick()))

        self.tasks.append(asyncio.ensure_future(self.stream_canbus(self.client)))
        self.tasks.append(asyncio.ensure_future(self.send_can_msgs(self.client)))
        self.tasks.append(asyncio.ensure_future(self.client.poll_service_state()))
        return await asyncio.gather(run_wrapper(), *self.tasks)

    async def send_can_msgs(self, client: CanbusClient) -> None:
        """This task ensures the canbus client sendCanbusMessage method has the pose_generator it will use to send
        messages on the can bus."""
        while True:
            if client.state.value != canbus_pb2.CanbusServiceState.RUNNING:
                logging.debug("Controller requires running canbus service")
                client.stub.sendCanbusMessage(self.pose_generator())
            await asyncio.sleep(0.25)

    async def pose_generator(self, period: float = 0.02):
        """The pose generator yields an AmigaAmigaRpdo1 (auto control command) for the canbus client to send on the
        bus at the specified period (recommended 50hz) based on the onscreen joystick position."""
        while True:
            rpdo1 = AmigaRpdo1(
                state_req=AmigaControlState.STATE_AUTO_ACTIVE,
                cmd_speed=self.max_speed * self.joystick_pose[1],
                cmd_ang_rate=self.max_angular_rate * self.joystick_pose[0],
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
