import argparse
import asyncio
import logging

from farm_ng import Amiga

async def main(address: str, track: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    
    try:
        logging.info(f"Sending request to repeat route at path: {track}")
        await amiga.repeat_route(track)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and stream camera data"
    )
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga robot"
    )
    
    parser.add_argument(
        "--track",
        type=str,
        required=True,
        help="Path to the track to be repeated; This example uses tracks recorded by the cask recorder or Python track recorder example"
    )

    args = parser.parse_args()
    asyncio.run(main(args.address, args.track))