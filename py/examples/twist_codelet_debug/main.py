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
# Licensed under the Amiga Development Kit License
import argparse
import asyncio
import time
from math import cos
from math import sin
from pathlib import Path

import matplotlib.pyplot as plt
from farm_ng.canbus.canbus_pb2 import Twist2d
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.events_file_reader import proto_from_json_file


# Integrate poses from velocities
def integrate_poses(stamps, twists):
    """Integrate poses from velocities.

    Args:
        stamps (list): List of timestamps.
        twists (list): List of Twist2d messages.
    """
    x_pose, y_pose, heading_pose = 0.0, 0.0, 0.0
    poses = []
    for i in range(1, len(stamps)):
        delta_time = stamps[i] - stamps[i - 1]
        x_pose += twists[i].linear_velocity_x * delta_time * cos(heading_pose)
        y_pose += twists[i].linear_velocity_x * delta_time * sin(heading_pose)
        heading_pose += twists[i].angular_velocity * delta_time
        poses.append((x_pose, y_pose, heading_pose))
    return list(zip(*poses)) if poses else ([], [], [])


async def stream_canbus(config: EventServiceConfig, stop_event: asyncio.Event, data_collections: dict):
    """Stream data from the CAN bus subscription.

    Args:
        config (EventServiceConfig): The configuration for the event client.
        stop_event (asyncio.Event): Event to signal stopping the task.
        data_collections (dict): Dictionary to store data for twist, twist_recv, and twist_send.
    """
    start_time = time.monotonic()
    last_twist_send = time.monotonic() - start_time

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        current_time = time.monotonic() - start_time
        if stop_event.is_set():
            break
        if current_time - last_twist_send > 5.0:
            stop_event.set()
            break
        if isinstance(message, Twist2d):
            if event.uri.path == "/twist":
                data_collections['twist_data'].append(message)
                data_collections['twist_stamps'].append(current_time)
            elif event.uri.path == "/twist_recv":
                data_collections['twist_recv_data'].append(message)
                data_collections['twist_recv_stamps'].append(current_time)
            elif event.uri.path == "/twist_send":
                data_collections['twist_send_data'].append(message)
                data_collections['twist_send_stamps'].append(current_time)
                last_twist_send = current_time


async def stream_filter(config: EventServiceConfig, stop_event: asyncio.Event, state_data, state_stamps):
    """Stream data from the filter subscription.

    Args:
        config (EventServiceConfig): The configuration for the event client.
        stop_event (asyncio.Event): Event to signal stopping the task.
        state_data (list): List to store processed state data.
        state_stamps (list): List to store timestamps for state data.
    """
    start_time = time.monotonic()

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        current_time = time.monotonic() - start_time
        if stop_event.is_set():
            break

        if event.uri.path == "/state":
            linear_velocity_x = message.pose.tangent_of_b_in_a.linear_velocity.x
            angular_velocity = message.pose.tangent_of_b_in_a.angular_velocity.z
            twist_message = Twist2d(linear_velocity_x=linear_velocity_x, angular_velocity=angular_velocity)
            state_data.append(twist_message)
            state_stamps.append(current_time)

        if not message.has_converged:
            print("Filter is not converged...")


async def main(service_config_path: Path) -> None:
    """Collect and plot data from multiple sources.

    Args:
        service_config_path (Path): The path to the service config list.
    """
    # Load configuration
    config_list: EventServiceConfigList = proto_from_json_file(service_config_path, EventServiceConfigList())
    canbus_config = config_list.configs[0]
    filter_config = config_list.configs[1]

    # Data storage for twist topics and state data
    data_collections = {
        'twist_data': [],
        'twist_stamps': [],
        'twist_recv_data': [],
        'twist_recv_stamps': [],
        'twist_send_data': [],
        'twist_send_stamps': [],
    }
    state_data, state_stamps = [], []

    stop_event = asyncio.Event()

    # Create tasks for streaming
    canbus_task = asyncio.create_task(stream_canbus(canbus_config, stop_event, data_collections))
    filter_task = asyncio.create_task(stream_filter(filter_config, stop_event, state_data, state_stamps))

    await asyncio.gather(canbus_task, filter_task)

    twist_poses = integrate_poses(data_collections['twist_stamps'], data_collections['twist_data'])
    twist_recv_poses = integrate_poses(data_collections['twist_recv_stamps'], data_collections['twist_recv_data'])
    twist_send_poses = integrate_poses(data_collections['twist_send_stamps'], data_collections['twist_send_data'])
    state_poses = integrate_poses(state_stamps, state_data)

    # Plot the collected data
    fig, axs = plt.subplots(5, 1, figsize=(14, 22))

    # Subplot 1: Linear Velocities
    axs[0].plot(
        data_collections['twist_stamps'], [x.linear_velocity_x for x in data_collections['twist_data']], label='/twist'
    )
    axs[0].plot(
        data_collections['twist_recv_stamps'],
        [x.linear_velocity_x for x in data_collections['twist_recv_data']],
        label='/twist_recv',
    )
    axs[0].plot(
        data_collections['twist_send_stamps'],
        [x.linear_velocity_x for x in data_collections['twist_send_data']],
        label='/twist_send',
    )
    axs[0].plot(state_stamps, [x.linear_velocity_x for x in state_data], label='/state')
    axs[0].set_xlabel('Time (s)')
    axs[0].set_ylabel('Linear Velocity (m/s)')
    axs[0].legend()
    axs[0].set_title('Linear Velocity Over Time')

    # Subplot 2: Angular Velocities
    axs[1].plot(
        data_collections['twist_stamps'], [x.angular_velocity for x in data_collections['twist_data']], label='/twist'
    )
    axs[1].plot(
        data_collections['twist_recv_stamps'],
        [x.angular_velocity for x in data_collections['twist_recv_data']],
        label='/twist_recv',
    )
    axs[1].plot(
        data_collections['twist_send_stamps'],
        [x.angular_velocity for x in data_collections['twist_send_data']],
        label='/twist_send',
    )
    axs[1].plot(state_stamps, [x.angular_velocity for x in state_data], label='/state')
    axs[1].set_xlabel('Time (s)')
    axs[1].set_ylabel('Angular Velocity (rad/s)')
    axs[1].legend()
    axs[1].set_title('Angular Velocity Over Time')

    # Subplot 3: Heading
    if twist_poses[2]:
        axs[2].plot(data_collections['twist_stamps'][1:], twist_poses[2], label='/twist heading')
    if twist_recv_poses[2]:
        axs[2].plot(data_collections['twist_recv_stamps'][1:], twist_recv_poses[2], label='/twist_recv heading')
    if twist_send_poses[2]:
        axs[2].plot(data_collections['twist_send_stamps'][1:], twist_send_poses[2], label='/twist_send heading')
    if state_poses[2]:
        axs[2].plot(state_stamps[1:], state_poses[2], label='/state heading')
    axs[2].set_xlabel('Time (s)')
    axs[2].set_ylabel('Heading (rad)')
    axs[2].legend()
    axs[2].set_title('Heading Over Time')

    # Subplot 4: x vs y Scatter Plot with Color Coding for Progression
    if twist_poses[0]:
        axs[3].scatter(
            twist_poses[0],
            twist_poses[1],
            c=range(len(twist_poses[0])),
            cmap='viridis',
            label='/twist',
            s=10,
            marker='o',
        )
    if twist_recv_poses[0]:
        axs[3].scatter(
            twist_recv_poses[0],
            twist_recv_poses[1],
            c=range(len(twist_recv_poses[0])),
            cmap='plasma',
            label='/twist_recv',
            s=10,
            marker='x',
        )
    if twist_send_poses[0]:
        axs[3].scatter(
            twist_send_poses[0],
            twist_send_poses[1],
            c=range(len(twist_send_poses[0])),
            cmap='cividis',
            label='/twist_send',
            s=10,
            marker='^',
        )
    if state_poses[0]:
        axs[3].scatter(
            state_poses[0], state_poses[1], c=range(len(state_poses[0])), cmap='cool', label='/state', s=10, marker='s'
        )
    axs[3].set_xlabel('x position (m)')
    axs[3].set_ylabel('y position (m)')
    axs[3].legend()
    axs[3].set_title('x vs y Position with Color Progression')

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python main.py", description="Stream motor states from the CAN bus and state filter."
    )
    parser.add_argument("--service-config", type=Path, required=True, help="The path to the service config list.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.service_config))
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
