"""Example of a camera service client."""
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
import time
from pathlib import Path

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file


async def with_timeout(aiter, timeout):
    """Helper function to iterate with a timeout."""
    it = aiter.__aiter__()
    while True:
        try:
            result = await asyncio.wait_for(it.__anext__(), timeout)
            yield result
        except StopAsyncIteration:
            break
        except asyncio.TimeoutError:
            print("Subscription timed out. No messages received within the timeout period.")
            return


async def monitor_connection(config: EventServiceConfig, duration: int) -> int:
    """Monitor the connection for a specified duration.

    Args:
        config (EventServiceConfig): The configuration for the event service.
        duration (int): The duration to monitor in seconds.

    Returns:
        int: The number of missed frames.
    """
    start = time.monotonic()
    last_stamp: float | None = None
    missed_frames = 0
    subscription_timeout = 15.0  # Timeout for waiting for each event

    while time.monotonic() - start < duration:
        try:
            async for event, message in with_timeout(
                EventClient(config).subscribe(config.subscriptions[0], decode=True), subscription_timeout
            ):
                now = time.monotonic()
                if last_stamp is None:
                    last_stamp = now

                # We stream at 3 fps, so if we haven't received a frame in 0.3 seconds, we consider it a missed frame.
                if now - last_stamp > 0.35:
                    missed_frames += 1

                if now - start > duration:
                    break

                if now - last_stamp > 3.0:
                    print(f"Breaking due to timeout. Last frame received {now - last_stamp} seconds ago.")
                    break

                if event.timestamps:
                    last_stamp = now

                time_elapsed = now - start
                hours, remainder = divmod(time_elapsed, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_formatted = f"{int(hours):02}:{int(minutes):02}:{seconds:06.3f}"
                print(f"Total time elapsed: {time_formatted}")
        except asyncio.TimeoutError:
            print("Subscription timed out. Attempting to reconnect...")
            await asyncio.sleep(5)  # Wait before attempting to reconnect
        except asyncio.CancelledError:
            print("Subscription cancelled.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    return missed_frames


async def attempt_monitor_connection(config: EventServiceConfig, duration: int, max_retries: int = 3) -> int:
    """Attempt to monitor the connection with retries.

    Args:
        config (EventServiceConfig): The configuration for the event service.
        duration (int): The duration to monitor in seconds.
        max_retries (int): The maximum number of retries.

    Returns:
        int: The number of missed frames.
    """
    for attempt in range(max_retries):
        try:
            missed_frames = await monitor_connection(config, duration)
            return missed_frames
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print("Waiting for 5 seconds before retrying...")
                await asyncio.sleep(5)
    print("Failed to connect after maximum retries.")
    return -1  # Indicate failure to connect


async def main(service_config_path: Path) -> None:
    """Run the camera service client.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    monitor_duration = 1 * 30
    wait_durations = [
        3,
        17,
        301,
        301,
        1,
        301,
        400,
    ]  # Random wait durations, but at least two larger than 300 s (grace period)
    repeat_count = len(wait_durations)

    for i in range(repeat_count):
        print(f"--- Monitoring session {i + 1}/{repeat_count} ---")
        missed_frames = await attempt_monitor_connection(config, monitor_duration)
        print(f"Session {i + 1} complete. Missed frames: {missed_frames}")

        if i < repeat_count - 1:
            wait_duration = wait_durations[i]
            print(f"Waiting for {wait_duration} seconds before the next session...")
            await asyncio.sleep(wait_duration)

    print("All monitoring sessions complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-stream.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.service_config))
    except KeyboardInterrupt:
        print("Interrupted by user")
