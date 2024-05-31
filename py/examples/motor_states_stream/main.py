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
    # Create a client to the LiDAR service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=False):
        print(f"Event: {event}")
        decoded_message = decode_vlp16_data(message)
        print(f"Decoded Message: {decoded_message}")
        print("-"*50)

def decode_vlp16_data(raw_data: bytes):
    """Decodes the VLP-16 raw data."""
    if len(raw_data) != 1209:
        return {'type': 'Unknown', 'timestamp': None, 'data': raw_data}

    # Extract timestamp from the first 8 bytes
    timestamp, = struct.unpack('d', raw_data[:8])
    
    # Extract the data from the remaining bytes
    data = raw_data[8:]

    if len(data) == 1201:
        return {'type': 'Vlp16RawData', 'timestamp': timestamp, 'data': parse_vlp16_data(data)}
    elif len(data) == 507:
        return {'type': 'Vlp16RawPosition', 'timestamp': timestamp, 'data': parse_vlp16_data(data)}
    else:
        return {'type': 'Unknown', 'timestamp': timestamp, 'data': data}

def parse_vlp16_data(data: bytes):
    """Parses the VLP-16 data blocks."""
    blocks = []
    for i in range(12):
        block = data[i*100:(i+1)*100]
        header, azimuth = struct.unpack_from('<HH', block, 0)
        channels = []
        for j in range(32):
            offset = 4 + j * 3
            distance, reflectivity = struct.unpack_from('<HB', block, offset)
            channels.append((distance, reflectivity))
        blocks.append({
            'header': header,
            'azimuth': azimuth / 100.0,  # azimuth is in hundredths of a degree
            'channels': channels
        })
    return blocks

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Stream LiDAR data from the LiDAR service.")
    parser.add_argument("--service-config", type=Path, required=True, help="The LiDAR service config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
