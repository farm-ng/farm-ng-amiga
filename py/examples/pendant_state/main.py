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

from farm_ng.canbus import amiga_v6_pb2
from farm_ng.canbus.packet import PendantButtons
from farm_ng.canbus.packet import PendantState
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file


async def main(service_config_path: Path) -> None:
    """Run the canbus service client.

    Args:
        service_config_path (Path): The path to the canbus service config.
    """

    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    async for event, msg in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        if not isinstance(msg, amiga_v6_pb2.PendantState):
            print(f"Unexpected message type: {type(msg)}")
            continue
        pendant_state: PendantState = PendantState.from_proto(msg)
        print(f"Received pendant state: {pendant_state}")
        for button in PendantButtons:
            if pendant_state.is_button_pressed(button):
                print(f"Button {button.name} is pressed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python main.py", description="Stream PendantState messages from the canbus service."
    )
    parser.add_argument("--service-config", type=Path, required=True, help="The canbus service config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
