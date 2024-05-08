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
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from farm_ng.canbus.tool_control_pb2 import ActuatorCommands
from farm_ng.canbus.tool_control_pb2 import HBridgeCommand
from farm_ng.canbus.tool_control_pb2 import HBridgeCommandType
from farm_ng.canbus.tool_control_pb2 import PtoCommand
from farm_ng.canbus.tool_control_pb2 import PtoCommandType
from farm_ng.canbus.tool_control_pb2 import ToolStatuses
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from pynput import keyboard


class KeyboardListener:
    def __init__(self):
        self.pressed_keys = set()
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)

    def on_press(self, key):
        try:
            key_name = key.char
        except AttributeError:
            key_name = key.name  # For special keys
        self.pressed_keys.add(key_name)

    def on_release(self, key):
        try:
            key_name = key.char
        except AttributeError:
            key_name = key.name  # For special keys
        self.pressed_keys.discard(key_name)

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()


def tool_control_from_key_presses(pressed_keys: set) -> ActuatorCommands:
    if 'space' in pressed_keys:
        print("Set all to passive with empty command")
        return ActuatorCommands()

    commands: ActuatorCommands = ActuatorCommands()

    # H-bridges controlled with 0, 1, 2, 3 & up / down arrows
    # up = forward, down = reverse, both = stop, neither / not pressed => omitted => passive
    if 'up' in pressed_keys and 'down' in pressed_keys:
        for hbridge_id in pressed_keys & {'0', '1', '2', '3'}:
            commands.hbridges.append(HBridgeCommand(id=int(hbridge_id), command=HBridgeCommandType.HBRIDGE_STOPPED))
    elif 'up' in pressed_keys:
        for hbridge_id in pressed_keys & {'0', '1', '2', '3'}:
            commands.hbridges.append(HBridgeCommand(id=int(hbridge_id), command=HBridgeCommandType.HBRIDGE_FORWARD))
    elif 'down' in pressed_keys:
        for hbridge_id in pressed_keys & {'0', '1', '2', '3'}:
            commands.hbridges.append(HBridgeCommand(id=int(hbridge_id), command=HBridgeCommandType.HBRIDGE_REVERSE))

    # PTOs controlled with a, b, c, d & left / right arrows
    # left = forward, right = reverse, both = stop, neither / not pressed => omitted => passive
    pto_id_mapping = {'a': 0x0, 'b': 0x1, 'c': 0x2, 'd': 0x3}
    pto_rpm: float = 20.0
    if 'left' in pressed_keys and 'right' in pressed_keys:
        for pto_char in pressed_keys & {'a', 'b', 'c', 'd'}:
            pto_id = pto_id_mapping[pto_char]
            commands.ptos.append(PtoCommand(id=pto_id, command=PtoCommandType.PTO_STOPPED, rpm=pto_rpm))
    elif 'left' in pressed_keys:
        for pto_char in pressed_keys & {'a', 'b', 'c', 'd'}:
            pto_id = pto_id_mapping[pto_char]
            commands.ptos.append(PtoCommand(id=pto_id, command=PtoCommandType.PTO_FORWARD, rpm=pto_rpm))
    elif 'right' in pressed_keys:
        for pto_char in pressed_keys & {'a', 'b', 'c', 'd'}:
            pto_id = pto_id_mapping[pto_char]
            commands.ptos.append(PtoCommand(id=pto_id, command=PtoCommandType.PTO_REVERSE, rpm=pto_rpm))

    return commands


async def control_tools(service_config_path: Path, keyboard_listener: KeyboardListener) -> None:
    """Control the tools / actuators on your Amiga.

    Args:
        service_config_path (Path): The path to the canbus service config.
        keyboard_listener (KeyboardListener): The keyboard listener.
    """
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    client: EventClient = EventClient(config)

    while True:
        # Send the tool control command
        commands: ActuatorCommands = tool_control_from_key_presses(keyboard_listener.pressed_keys)
        await client.request_reply("/control_tools", commands, decode=True)

        # Sleep for a bit
        await asyncio.sleep(0.1)


async def stream_tool_statuses(service_config_path: Path) -> None:
    """Stream the tool statuses.

    Args:
        service_config_path (Path): The path to the canbus service config.
    """

    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    message: ToolStatuses
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        print("###################")
        print(message)


async def run(service_config_path: Path, keyboard_listener: KeyboardListener):
    # Create tasks for both functions
    tasks: list[asyncio.Task] = [
        asyncio.create_task(control_tools(service_config_path, keyboard_listener)),
        asyncio.create_task(stream_tool_statuses(service_config_path)),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python main.py", description="Command and monitor tools with the canbus service."
    )
    parser.add_argument("--service-config", type=Path, required=True, help="The canbus service config.")
    args = parser.parse_args()

    keyboard_listener = KeyboardListener()
    keyboard_listener.start()

    try:
        asyncio.run(run(args.service_config, keyboard_listener))
    except KeyboardInterrupt:
        pass
    finally:
        keyboard_listener.stop()
