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

from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.service.service_client import ClientConfig


async def request_generator(twist: canbus_pb2.Twist2d) -> iter[canbus_pb2.SendVehicleTwistCommandReply]:
    while True:
        yield canbus_pb2.SendVehicleTwistCommandRequest(command=twist)
        await asyncio.sleep(0.1)  # Limit to 10 hz


async def main(config: ClientConfig, twist: canbus_pb2.Twist2d) -> None:
    # Connect to the robot
    client = CanbusClient(config)

    # get the tiwst command stream
    stream = client.stub.sendVehicleTwistCommand(request_generator(twist))

    # print the stream results
    async for twist_state in stream:
        print(twist_state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', default='localhost')
    parser.add_argument('--port', default=50060)
    parser.add_argument("--vel-x", type=float, default=0.0)
    parser.add_argument("--theta", type=float, default=0.0)
    args = parser.parse_args()

    # create the twist command
    twist = canbus_pb2.Twist2d(linear_velocity_x=args.vel_x, angular_velocity=args.theta)

    asyncio.run(main(ClientConfig(address=args.address, port=args.port), twist))
