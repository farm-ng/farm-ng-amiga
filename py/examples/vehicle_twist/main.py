from __future__ import annotations
import argparse
import asyncio
import time
from pathlib import Path
from farm_ng.canbus.canbus_pb2 import Twist2d
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file

async def main(service_config_path: Path) -> None:
    """Run the camera service client.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    # Initialize the command to send
    twist = Twist2d(linear_velocity_x=1.0, angular_velocity=0.0)

    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    client: EventClient = EventClient(config)
    now = time.time()
    elapsed = 0.0

    while elapsed < 5.0:
        # Command the robot dro drive forward
        print(f"Sending linear velocity: {twist.linear_velocity_x:.2f}, angular velocity: {twist.angular_velocity:.2f}")
        await client.request_reply("/twist", twist)

        # Sleep to maintain a constant rate
        await asyncio.sleep(0.1)
        elapsed = time.time() - now
    # Stop the vehicle
    twist_stop = Twist2d(linear_velocity_x=0.0, angular_velocity=0.0)
    print("Stopping the vehicle")
    await client.request_reply("/twist", twist_stop)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Send twist commands to control Amiga through the canbus service.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
