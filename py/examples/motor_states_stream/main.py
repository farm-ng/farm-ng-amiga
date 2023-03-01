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
from typing import List

import grpc
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.canbus.packet import MotorState
from farm_ng.service import service_pb2
from farm_ng.service.service_client import ClientConfig


class MotorStatesApp:
    def __init__(self, address: str, canbus_port: int) -> None:
        self.address: str = address
        self.canbus_port: int = canbus_port

        self.async_tasks: List[asyncio.Task] = []

    async def app_func(self):
        # configure the canbus client
        canbus_config: ClientConfig = ClientConfig(address=self.address, port=self.canbus_port)
        canbus_client: CanbusClient = CanbusClient(canbus_config)
        await asyncio.gather(self.stream_motors(canbus_client))

    async def stream_motors(self, client: CanbusClient) -> None:
        """This task:

        - listens to the canbus client's stream
        - filters for AmigaTpdo1 messages
        - extracts useful values from AmigaTpdo1 messages
        """

        response_stream = None

        while True:
            # check the state of the service
            state = await client.get_state()

            if state.value not in [service_pb2.ServiceState.IDLE, service_pb2.ServiceState.RUNNING]:
                if response_stream is not None:
                    response_stream.cancel()
                    response_stream = None

                print("Canbus service is not streaming or ready to stream")
                await asyncio.sleep(0.1)
                continue

            if response_stream is None and state.value != service_pb2.ServiceState.UNAVAILABLE:
                # get the streaming object
                response_stream = client.stream_motors()

            try:
                # try/except so app doesn't crash on killed service
                response: canbus_pb2.StreamCanbusReply = await response_stream.read()
                assert response and response != grpc.aio.EOF, "End of stream"
            except Exception as e:
                print(e)
                response_stream.cancel()
                response_stream = None
                continue

            print('--')
            for motor in response.motors:
                print(MotorState.from_proto(motor))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="virtual-joystick")
    parser.add_argument("--address", type=str, default="localhost", help="The server address")
    parser.add_argument(
        "--canbus-port", type=int, required=True, help="The grpc port where the canbus service is running."
    )

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(MotorStatesApp(args.address, args.canbus_port).app_func())
    except asyncio.CancelledError:
        pass
    loop.close()
