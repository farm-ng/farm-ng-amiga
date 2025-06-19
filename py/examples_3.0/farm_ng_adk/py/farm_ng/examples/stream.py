import argparse
import asyncio
import logging
import numpy as np

from farm_ng import Amiga, nexus as apb

async def stream_callback(stream: apb.Stream) -> None:
    frame = stream.video
    if frame is not None:
        logging.info(f"[{frame.frame_id}] '{frame.format}' len={len(frame.data)}")

async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)

    try:
        async with amiga.stream_sub(stream_callback):
            logging.info("Started streaming...")

            # Create an event to control how long we run
            stop_event = asyncio.Event()

            # Wait until Ctrl+C
            try:
                await stop_event.wait()
            except KeyboardInterrupt:
                logging.info("Stopping stream...")
            finally:
                handler.cleanup()

        logging.info("Streaming session completed successfully.")

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

    args = parser.parse_args()
    asyncio.run(main(args.address))
