# Licensed under the Amiga Development Kit License

import argparse
import asyncio
import time
from pathlib import Path
import matplotlib.pyplot as plt
from math import cos, sin
from farm_ng.canbus.canbus_pb2 import Twist2d
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file

async def main(service_config_path: Path, data_time: float) -> None:
    """Collect and plot data from the twist, twist_recv, and twist_send topics.

    Args:
        service_config_path (Path): The path to the service config.
        data_time (float): Duration to collect data (in seconds).
    """
    # Load configuration
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    # Data storage for twist topics
    twist_data, twist_stamps = [], []
    twist_recv_data, twist_recv_stamps = [], []
    twist_send_data, twist_send_stamps = [], []

    start_time = time.monotonic()

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        current_time = time.monotonic() - start_time
        if current_time > data_time:
            break
        
        if isinstance(message, Twist2d):
            if event.uri.path == "/twist":
                twist_data.append(message)
                twist_stamps.append(current_time)
            elif event.uri.path == "/twist_recv":
                twist_recv_data.append(message)
                twist_recv_stamps.append(current_time)
            elif event.uri.path == "/twist_send":
                twist_send_data.append(message)
                twist_send_stamps.append(current_time)

        if current_time > data_time:
            break

    # Integrate poses from velocities
    def integrate_poses(stamps, twists):
        x_pose, y_pose, heading_pose = 0.0, 0.0, 0.0
        poses = []
        for i in range(1, len(stamps)):
            delta_time = stamps[i] - stamps[i - 1]
            x_pose += twists[i].linear_velocity_x * delta_time * cos(heading_pose)
            y_pose += twists[i].linear_velocity_x * delta_time * sin(heading_pose)
            heading_pose += twists[i].angular_velocity * delta_time
            poses.append((x_pose, y_pose, heading_pose))
        return list(zip(*poses)) if poses else ([], [], [])

    twist_poses = integrate_poses(twist_stamps, twist_data)
    twist_recv_poses = integrate_poses(twist_recv_stamps, twist_recv_data)
    twist_send_poses = integrate_poses(twist_send_stamps, twist_send_data)

    # Plot the collected data
    plt.figure(figsize=(14, 10))

    # Subplot 1: Velocities
    plt.subplot(2, 1, 1)
    plt.plot(twist_stamps, [x.linear_velocity_x for x in twist_data], label='/twist')
    plt.plot(twist_recv_stamps, [x.linear_velocity_x for x in twist_recv_data], label='/twist_recv')
    plt.plot(twist_send_stamps, [x.linear_velocity_x for x in twist_send_data], label='/twist_send')
    plt.xlabel('Time (s)')
    plt.ylabel('linear_velocity_x')
    plt.legend()
    plt.title('Twist Data Over Time')

    # Subplot 2: Poses
    plt.subplot(2, 1, 2)
    if twist_poses[0]:
        plt.plot(twist_stamps[1:], twist_poses[0], label='/twist x position')
        plt.plot(twist_stamps[1:], twist_poses[1], label='/twist y position')
        plt.plot(twist_stamps[1:], twist_poses[2], label='/twist heading')
    if twist_recv_poses[0]:
        plt.plot(twist_recv_stamps[1:], twist_recv_poses[0], label='/twist_recv x position')
        plt.plot(twist_recv_stamps[1:], twist_recv_poses[1], label='/twist_recv y position')
        plt.plot(twist_recv_stamps[1:], twist_recv_poses[2], label='/twist_recv heading')
    if twist_send_poses[0]:
        plt.plot(twist_send_stamps[1:], twist_send_poses[0], label='/twist_send x position')
        plt.plot(twist_send_stamps[1:], twist_send_poses[1], label='/twist_send y position')
        plt.plot(twist_send_stamps[1:], twist_send_poses[2], label='/twist_send heading')
    plt.xlabel('Time (s)')
    plt.ylabel('Pose')
    plt.legend()
    plt.title('Poses Derived from Velocities')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Stream motor states from the canbus service.")
    parser.add_argument("--service-config", type=Path, required=True, help="The path to the service config.")
    parser.add_argument("--data-time", type=float, required=True, help="Duration to collect data (in seconds).")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.service_config, args.data_time))
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
