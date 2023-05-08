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

from farm_ng.oak import oak_pb2
from farm_ng.oak.camera_client import OakCameraClient
from farm_ng.service import service_pb2
from farm_ng.service.service_client import ClientConfig


async def main(address: str, port: int) -> None:
    # create a client to the camera service
    config = ClientConfig(address=address, port=port)
    client = OakCameraClient(config)

    # check the service is in a valid state to run this test
    state = await client.get_state()
    if state.value not in [service_pb2.ServiceState.IDLE, service_pb2.ServiceState.RUNNING]:
        print("Service is not in a valid state to run this test.")
        return

    # get the calibration message
    response: oak_pb2.GetCalibrationReply = await client.get_calibration()
    calibration: oak_pb2.OakCalibration = response.calibration
    print(calibration)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-camera-calibration")
    parser.add_argument("--port", type=int, required=True, help="The camera port.")
    parser.add_argument("--address", type=str, default="localhost", help="The camera address")
    args = parser.parse_args()

    asyncio.run(main(args.address, args.port))
