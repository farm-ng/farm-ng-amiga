import argparse
import asyncio
import logging

from farm_ng import Amiga, nexus as apb

async def feedback_callback(feedback: apb.Feedback) -> None:
    logging.info(f"Received feedback: {feedback}")

async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)

    try:
        async with amiga.feedback_sub(feedback_callback):
            logging.info("Listening to feedback...")

            # Create an event to control how long we run
            stop_event = asyncio.Event()

            # Wait for Ctrl+C
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=3)
            except asyncio.TimeoutError:
                logging.info("Finished")

        logging.info("Feedback session completed successfully.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and listen to feedback"
    )
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga"
    )

    args = parser.parse_args()

    asyncio.run(main(args.address))
