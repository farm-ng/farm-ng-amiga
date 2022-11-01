# Copyright (c) farm-ng, inc. All rights reserved.
import argparse
import asyncio
import os
from typing import List

from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.canbus.canbus_client import CanbusClientConfig
from farm_ng.canbus.packet import AmigaTpdo1

# from farm_ng.canbus import canbus_pb2
# from farm_ng.canbus.canbus_client import CanbusServiceState

os.environ["KIVY_NO_ARGS"] = "1"


from kivy.config import Config  # noreorder # noqa: E402

Config.set("graphics", "fullscreen", "false")

from kivy.app import App  # noqa: E402
from kivy.lang.builder import Builder  # noqa: E402
from kivy.graphics import Color, Ellipse  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.input.providers.mouse import MouseMotionEvent  # noqa: E402

# from kivy.uix.widget import Widget  # noqa: E402

kv = """
# <VirtualJoystickWidget@Widget>:
BoxLayout:
    BoxLayout:
        size_hint_x: 0.3
        orientation: 'vertical'
        Label:
            text: "state: " + str(app.amiga_tpdo1.state)
        Label:
            text: "speed: " + str(app.amiga_tpdo1.meas_speed) + " [m/s]"
        Label:
            text: "angular rate: " + str(app.amiga_tpdo1.meas_ang_rate) + " [rad/s]"
    # VirtualJoystickWidget:
    Widget:
        id: joystick
"""


class VirtualPendantApp(App):
    def __init__(self, address: str, port: int) -> None:
        super().__init__()
        self.address = address
        self.port = port

        self.tasks: List[asyncio.Task] = []

        self.amiga_tpdo1 = AmigaTpdo1()
        self.app = App.get_running_app()

        self.joystick_pose: tuple[float, float] = (0.0, 0.0)

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

            self.joystick_pose = (-1.0 + 2.0 * (touch.sx - 0.3) / 0.7, -1.0 + 2.0 * touch.sy)
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

    async def draw_joystick(self):
        while self.root is None:
            await asyncio.sleep(0.01)
            widget = self.app.root.ids["joystick"]
        while True:
            widget.canvas.clear()
            size = (100, 100)
            widget.canvas.add(Color(1.0, 1.0, 0.0, 1.0, mode="rgba"))
            x_abs, y_abs = (
                widget.center_x + 0.5 * self.joystick_pose[0] * widget.width,
                widget.center_y + 0.5 * self.joystick_pose[1] * widget.size[1],
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
        # self.tasks.append(asyncio.ensure_future(self.client._poll_service_state()))
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
