import argparse
import asyncio
import logging

from farm_ng import Amiga

def parse_direction(direction: str) -> str:
    """Parse the direction input and return a corresponding command."""
    if direction == 'l' or direction == 'left':
        return "left"
    elif direction == 'r' or direction == 'right':
        return "right"
    else:
        raise ValueError("Invalid direction. Use 'l' for left or 'r' for right.")

async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    
    try:
        direction_input = input("Enter 'l' or 'r' to drive a square track (left/right): ").strip().lower()
        
        direction = parse_direction(direction_input)
        
        logging.info(f"Sending request to drive a square track to the {direction}")
        await amiga.square_track(direction)
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and record data"
    )
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga"
    )

    args = parser.parse_args()

    asyncio.run(main(args.address))