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
import struct
from pathlib import Path

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file


async def main(service_config_path: Path) -> None:
    """Run the LiDAR service client.

    Args:
        service_config_path (Path): The path to the LiDAR service config.
    """
    position = True
    data = True
    # Create a client to the LiDAR service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=False):
        if "position" in event.uri.path and position:
            print(f"Event: \n{event}")
            print("-" * 30)
            decoded_message = decode_message(message)
            print(f"Decoded Message: \n{format_message(decoded_message)}")
            print("-" * 50)
            position = False
        elif "data" in event.uri.path and data:
            print(f"Event: \n{event}")
            print("-" * 30)
            decoded_message = decode_message(message)
            print(f"Decoded Message: \n{format_message(decoded_message)}")
            print("-" * 50)
            data = False


def decode_message(raw_data: bytes):
    """Decodes the VLP-16 raw data."""
    if len(raw_data) == 1209:
        return decode_vlp16_data(raw_data)
    elif len(raw_data) == 515:
        return decode_vlp16_position(raw_data)
    else:
        return {'type': 'Unknown', 'timestamp': None, 'data': raw_data}


def decode_vlp16_data(raw_data: bytes):
    """Decodes the VLP-16 raw data."""
    # Extract timestamp from the first 8 bytes
    (timestamp,) = struct.unpack('d', raw_data[:8])

    # Extract the data from the remaining bytes
    data = raw_data[8:]

    return {'type': 'Vlp16RawData', 'timestamp': timestamp, 'data': parse_vlp16_data(data)}


def decode_vlp16_position(raw_data: bytes):
    """Decodes the VLP-16 raw position data."""
    # Extract timestamp from the first 8 bytes
    (timestamp,) = struct.unpack('d', raw_data[:8])

    # Extract the data from the remaining bytes
    data = raw_data[8:]

    return {'type': 'Vlp16RawPosition', 'timestamp': timestamp, 'data': list(data)}


def parse_vlp16_data(data: bytes):
    """Parses the VLP-16 data blocks."""
    blocks = []
    for i in range(12):
        block = data[i * 100 : (i + 1) * 100]
        header, azimuth = struct.unpack_from('<HH', block, 0)
        channels = []
        for j in range(32):
            offset = 4 + j * 3
            distance, reflectivity = struct.unpack_from('<HB', block, offset)
            channels.append((distance, reflectivity))
        blocks.append(
            {'header': header, 'azimuth': azimuth / 100.0, 'channels': channels}  # azimuth is in hundredths of a degree
        )
    return blocks


def format_message(decoded_message):
    """Formats the decoded message for better readability."""
    message_type = decoded_message.get('type', 'Unknown')
    timestamp = decoded_message.get('timestamp', 'None')
    data = decoded_message.get('data', [])

    output = [f"type: {message_type}", f"timestamp: {timestamp}", "data:"]
    if message_type == 'Vlp16RawData':
        for block in data:
            output.append(f"  - header: {block['header']}, azimuth: {block['azimuth']}")
            output.append("    channels:")
            for channel in block['channels']:
                output.append(f"      - distance: {channel[0]}, reflectivity: {channel[1]}")
    elif message_type == 'Vlp16RawPosition':
        output.append(f"  - raw position data: {data}")
    else:
        output.append(f"  - raw data: {data}")

    return "\n".join(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Stream LiDAR data from the LiDAR service.")
    parser.add_argument("--service-config", type=Path, required=True, help="The LiDAR service config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
