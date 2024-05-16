from __future__ import annotations

import argparse
import asyncio
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import numba as nb  # Importing numba for the unpacking function
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics

@nb.njit(parallel=True, cache=True)
def unpack_raw10(input: nb.uint8[::1], out: nb.uint16[::1], expand16bit: bool) -> nb.uint16[::1]:
    lShift = 6 if expand16bit else 0
    for i in nb.prange(input.size // 5):
        b4 = input[i * 5 + 4]
        out[i * 4]     = ((input[i * 5]     << 2) | ( b4       & 0x3)) << lShift
        out[i * 4 + 1] = ((input[i * 5 + 1] << 2) | ((b4 >> 2) & 0x3)) << lShift
        out[i * 4 + 2] = ((input[i * 5 + 2] << 2) | ((b4 >> 4) & 0x3)) << lShift
        out[i * 4 + 3] = ((input[i * 5 + 3] << 2) |  (b4 >> 6)       ) << lShift
    return out

async def main(service_config_path: Path) -> None:
    """Run the camera service client.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    timestamps = deque(maxlen=10)  # Store the last 10 timestamps

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        # Find the monotonic driver receive timestamp, or the first timestamp if not available.
        stamp = (
            get_stamp_by_semantics_and_clock_type(event, StampSemantics.DRIVER_RECEIVE, "monotonic")
            or event.timestamps[0].stamp
        )

        # Append the current timestamp
        timestamps.append(stamp)

        # Calculate FPS using the running average
        if len(timestamps) == timestamps.maxlen:
            time_deltas = [t2 - t1 for t1, t2 in zip(timestamps, list(timestamps)[1:])]
            average_delta = sum(time_deltas) / len(time_deltas)
            fps = 1 / average_delta if average_delta > 0 else 0
            print(f"FPS: {fps:.2f}")

        # Log the first few bytes of the image data for debugging
        print(f"First few bytes of image data: {message.image_data[:20]}")
        print(f"Raw data size: {len(message.image_data)}")

        # Initialize the image as None
        image = None

        # Check the event URI path to apply specific processing
        if event.uri.path == "/rgb":
            # Attempt to decode the RAW10 packed data
            try:
                raw_data = np.frombuffer(message.image_data, dtype=np.uint8)
                print(f"Raw data size: {raw_data.size}")
                unpacked_data = np.empty((raw_data.size // 5) * 4, dtype=np.uint16)
                unpacked_data = unpack_raw10(raw_data, unpacked_data, True)  # Set expand16bit to True
                
                # Print the size of unpacked data
                print(f"Size of unpacked data: {unpacked_data.size}")
                print(f"First few values of unpacked data: {unpacked_data[:20]}")
                
                # Try the expected resolution
                try:
                    bayer_image = unpacked_data.reshape((1080, 1920))
                    print(f"Successfully reshaped to resolution: (1080, 1920)")
                    
                    # Convert Bayer to RGB
                    image = cv2.cvtColor(bayer_image.astype(np.uint16), cv2.COLOR_BayerBG2BGR)
                except ValueError as e:
                    print(f"Failed to reshape to resolution (1080, 1920): {e}")
            except Exception as e:
                print(f"Error unpacking RAW10 data: {e}")
        else:
            # Handle mono images
            try:
                image = np.frombuffer(message.image_data, dtype=np.uint8).reshape(800, 1280)
            except ValueError:
                print("Error reshaping mono image")

        if event.uri.path == "/disparity":
            image = cv2.applyColorMap(image * 3, cv2.COLORMAP_JET)

        # Print the resolution of the image
        if image is not None:
            print(f"Resolution: {image.shape}")

            # visualize the image
            cv2.namedWindow("image", cv2.WINDOW_NORMAL)
            cv2.imshow("image", image)
            cv2.waitKey(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-camera-stream")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
