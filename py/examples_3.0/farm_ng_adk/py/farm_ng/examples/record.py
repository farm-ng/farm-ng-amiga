import argparse
import asyncio
import logging

from farm_ng import Amiga

async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)

    try:
        logging.info("Sending request to start recording")
        await amiga.start_recording(
            id="my_session",
            topics=[
                "annotations",
                "global_pose",
            ]
        )

        logging.info("Recording... Waiting 1 seconds.")
        await asyncio.sleep(1)

        logging.info("Recording some annotations")
        await amiga.record_annotations(context="test", items={
                "temperature": 23.5,
                "status": "running",
                "error_code": 0,
                "is_active": True
            })

        logging.info("Recording... Waiting 1 seconds.")
        await asyncio.sleep(1)

        logging.info("Sending request to stop recording")
        await amiga.stop_recording(
            id="my_session",
        )

        logging.info("Recording session completed successfully.")

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
