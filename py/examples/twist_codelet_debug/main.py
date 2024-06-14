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
import time
from pathlib import Path

import matplotlib.pyplot as plt
from farm_ng.canbus.canbus_pb2 import Twist2d
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file


async def main(service_config_path: Path, data_time: float) -> None:
    """Run the camera service client and collect data for 10 seconds.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    twist_data = []
    twist_stamps = []
    twist_recv_data = []
    twist_recv_stamps = []

    start_time = time.time()

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        if isinstance(message, Twist2d):
            if event.uri.path == "/twist":
                twist_data.append(message.linear_velocity_x)
                twist_stamps.append(time.time() - start_time)
            elif event.uri.path == "/twist_recv":
                twist_recv_data.append(message.linear_velocity_x)
                twist_recv_stamps.append(time.time() - start_time)
            print(f"Event: \n{event}")
            print("-" * 80)
            print(f"Message: \n{message}")

        # Check if the collection duration has elapsed
        if time.time() - start_time > data_time:
            break

    # Plot the collected data
    plt.figure()
    # plt.plot(twist_data, label='/twist')
    plt.plot(twist_stamps, twist_data, label='/twist')
    # plt.plot(twist_recv_data, label='/twist_recv')
    plt.plot(twist_recv_stamps, twist_recv_data, label='/twist_recv')
    plt.xlabel('Time (s)')
    plt.ylabel('linear_velocity_x')
    plt.legend()
    plt.title('Twist and Twist Recv Data')
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Stream motor states from the canbus service.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    parser.add_argument("--data-time", type=float, required=True, help="The camera config.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.service_config, args.data_time))
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
