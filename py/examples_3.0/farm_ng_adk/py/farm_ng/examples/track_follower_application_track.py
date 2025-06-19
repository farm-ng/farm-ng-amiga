import argparse
import asyncio
import logging
import time

from farm_ng import Amiga, nexus as apb

async def main(address: str, track: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    
    coords = []
    
    async def feedback_callback(feedback: apb.Feedback) -> None:
        if feedback.HasField("amiga_state"):
            state = feedback.amiga_state
            if state.HasField("global_pose"):
                pose = state.global_pose
                if pose.HasField("position"):
                    position = pose.position
                    
                    try:
                        coords_obj = {
                            "longitude": position.longitude,
                            "latitude": position.latitude,
                            "timestamp": time.monotonic()
                        }
                        coords.append(coords_obj)
                    except Exception as e:
                        logging.error(f"Error processing position: {e}")
    
    try:
        async def feedback_task():
             async with amiga.feedback_sub(feedback_callback):
                logging.info("Fetching Position...")
                 
                stop_event = asyncio.Event()

                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=3)
                except asyncio.TimeoutError:
                    logging.info("Finished")
                    
        await feedback_task()
        if coords:
            print(f"Current position: Latitude: {coords[-1]['latitude']}, Longitude: {coords[-1]['longitude']}")
        
        logging.info(f"Sending request to repeat route at path: {track}")
        await amiga.repeat_route_from_lon_lats(track)
        
        await asyncio.sleep(5)
        
        logging.info("Pausing route")
        await amiga.pause_route()
        
        await feedback_task()
        if coords:
            print(f"Current position: Latitude: {coords[-1]['latitude']}, Longitude: {coords[-1]['longitude']}")
            
        await asyncio.sleep(5)
            
        await amiga.repeat_route_from_lon_lats(track)
        
        await asyncio.sleep(5)
        
        await feedback_task()
        if coords:
            print(f"Current position: Latitude: {coords[-1]['latitude']}, Longitude: {coords[-1]['longitude']}")  
        
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