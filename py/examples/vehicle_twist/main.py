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

import cv2
from farm_ng.canbus.canbus_pb2 import Twist2d
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from numpy import clip

# NOTE: be careful with these values, they are in m/s and rad/s
MAX_LINEAR_VELOCITY_MPS = 0.5
MAX_ANGULAR_VELOCITY_RPS = 0.5
VELOCITY_INCREMENT = 0.05


def update_twist_with_key_press(twist: Twist2d, key: int):
    """Function to update the twist command based on the key pressed."""
    # Stop
    if key == ord(" "):
        twist.linear_velocity_x = 0.0
        twist.linear_velocity_y = 0.0
        twist.angular_velocity = 0.0

    # Forward / reverse
    if key == ord("w"):
        twist.linear_velocity_x += VELOCITY_INCREMENT
    elif key == ord("s"):
        twist.linear_velocity_x -= VELOCITY_INCREMENT

    # Left / right
    if key == ord("a"):
        twist.angular_velocity += VELOCITY_INCREMENT
    elif key == ord("d"):
        twist.angular_velocity -= VELOCITY_INCREMENT

    # Clip the velocities
    twist.linear_velocity_x = clip(twist.linear_velocity_x, -MAX_LINEAR_VELOCITY_MPS, MAX_LINEAR_VELOCITY_MPS)
    twist.angular_velocity = clip(twist.angular_velocity, -MAX_ANGULAR_VELOCITY_RPS, MAX_ANGULAR_VELOCITY_RPS)
    return twist


async def main(service_config_path: Path) -> None:
    """Run the canbus service client.

    Args:
        service_config_path (Path): The path to the canbus service config.
    """
    # Initialize the command to send
    twist = Twist2d()

    # open a window to capture key presses
    cv2.namedWindow('Virtual Keyboard')

    # create a client to the canbus service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    client: EventClient = EventClient(config)

    print(client.config)

    while True:
        key = cv2.waitKey(1)  # capture key press
        if key == ord("q"):
            break

        # Update and send the twist command
        twist = update_twist_with_key_press(twist, key)
        print(f"Sending linear velocity: {twist.linear_velocity_x:.3f}, angular velocity: {twist.angular_velocity:.3f}")
        await client.request_reply("/twist", twist)

        # Sleep to maintain a constant rate
        await asyncio.sleep(0.05)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python main.py", description="Send twist commands to control Amiga through the canbus service."
    )
    parser.add_argument("--service-config", type=Path, required=True, help="The canbus service config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
