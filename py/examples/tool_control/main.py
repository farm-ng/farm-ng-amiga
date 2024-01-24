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
from farm_ng.canbus.tool_control_pb2 import ToolStatuses
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from google.protobuf.empty_pb2 import Empty
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

    return commands


async def main(service_config_path: Path, keyboard_listener: KeyboardListener) -> None:
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    client: EventClient = EventClient(config)

    print(client.config)

    while True:
        # Send the tool control command
        commands: ActuatorCommands = tool_control_from_key_presses(keyboard_listener.pressed_keys)
        await client.request_reply("/control_tools", commands, decode=True)

        # Display the tool status
        tools_status = await client.request_reply("/get_tools_status", Empty(), decode=True)
        if not isinstance(tools_status, ToolStatuses):
            raise TypeError(f"Expected ToolStatuses, got {type(tools_status)}")
        print(tools_status)

        # Additional application logic here
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Command and monitor tools with the canbus service.")
    parser.add_argument("--service-config", type=Path, required=True, help="The canbus service config.")
    args = parser.parse_args()

    keyboard_listener = KeyboardListener()
    keyboard_listener.start()

    try:
        asyncio.run(main(args.service_config, keyboard_listener))
    except KeyboardInterrupt:
        pass
    finally:
        keyboard_listener.stop()
