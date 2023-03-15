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

import cv2
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.service.service_client import ClientConfig

# NOTE: becareful with these values, they are in m/s and rad/s
MAX_LINEAR_VELOCITY_MPS = 0.5
MAX_ANGULAR_VELOCITY_RPS = 0.5

VELOCITY_INCREMENT = 0.1


async def request_generator() -> iter[canbus_pb2.SendVehicleTwistCommandReply]:
    # the command to send
    twist = canbus_pb2.Twist2d()

    # open a window to capture key presses
    cv2.namedWindow('Virtual Keyboard')

    while True:
        key = cv2.waitKey(1)  # capture key presses

        if key == ord(" "):
            twist.linear_velocity_x = 0.0
            twist.linear_velocity_y = 0.0
            twist.angular_velocity = 0.0

        if key == ord("i"):
            twist.linear_velocity_x += VELOCITY_INCREMENT
            twist.linear_velocity_x = min(twist.linear_velocity_x, MAX_LINEAR_VELOCITY_MPS)
        elif key == ord("k"):
            twist.linear_velocity_x -= VELOCITY_INCREMENT
            twist.linear_velocity_x = max(twist.linear_velocity_x, -MAX_LINEAR_VELOCITY_MPS)

        if key == ord("j"):
            twist.angular_velocity += VELOCITY_INCREMENT
            twist.angular_velocity = min(twist.angular_velocity, MAX_ANGULAR_VELOCITY_RPS)
        elif key == ord("l"):
            twist.angular_velocity -= VELOCITY_INCREMENT
            twist.angular_velocity = max(twist.angular_velocity, -MAX_ANGULAR_VELOCITY_RPS)

        yield canbus_pb2.SendVehicleTwistCommandRequest(command=twist)
        await asyncio.sleep(0.1)


async def main(config: ClientConfig) -> None:
    # Connect to the robot
    client = CanbusClient(config)

    # get the tiwst command stream
    stream = client.stub.sendVehicleTwistCommand(request_generator())

    # print the stream results
    async for twist_state in stream:
        print(twist_state)
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', default='localhost')
    parser.add_argument('--port', default=50060)
    args = parser.parse_args()

    asyncio.run(main(ClientConfig(address=args.address, port=args.port)))
