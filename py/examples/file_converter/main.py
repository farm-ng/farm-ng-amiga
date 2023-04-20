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
import os
from pathlib import Path
from typing import List

import cv2
import numpy as np
from farm_ng.core import event_pb2
from farm_ng.core.events_file_reader import EventLogPosition
from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.oak import oak_pb2

DEFAULT_OUTPUT_PATH = os.path.dirname(os.path.realpath(__file__))


# helper function to filter valid events given a message type
def event_has_message(event: event_pb2.Event, msg_type) -> bool:
    return event.uri.query.split("&")[0].split(".")[-1] == msg_type.__name__


def main(file_name: Path, output_path: Path, camera_name: str, disparity_scale: int = 1) -> None:
    disparity_scale = max(1, int(disparity_scale))

    # create the file reader
    reader = EventsFileReader(file_name)
    assert reader.open()

    # Add nested directories to the output_path based on the events file name & camera name
    output_path = output_path / file_name.stem / camera_name
    # Create the output path, if it doesn't already exist
    output_path.mkdir(parents=True, exist_ok=True)

    # filter the events containing `oak_pb2.OakDataSample`
    events: List[EventLogPosition] = [
        x for x in reader.get_index() if event_has_message(x.event, oak_pb2.OakDataSample)
    ]

    # filter the image based events by camera name
    cam_events: List[EventLogPosition] = [x for x in events if x.event.uri.path == f"{camera_name}/video"]

    video_writers: dict[str, cv2.VideoWriter] = {}
    for event_log in cam_events:
        # parse the message
        sample: oak_pb2.OakDataSample
        sample = event_log.read_message()

        frame: oak_pb2.OakSyncFrame = sample.frame
        for view in ["rgb", "disparity", "left", "right"]:
            img = cv2.imdecode(np.frombuffer(getattr(frame, view).image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)
            if view == "disparity":
                img = cv2.applyColorMap(img * disparity_scale, cv2.COLORMAP_HOT)

            window_name: str = view + ":" + event_log.event.uri.query
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.imshow(window_name, img)
            height, width, _ = img.shape

            if view not in video_writers:
                video_writers[view] = cv2.VideoWriter(
                    str(output_path / (view + '.mp4')), cv2.VideoWriter_fourcc(*'mp4v'), 10, (width, height)
                )

            video_writers[view].write(img)

        cv2.waitKey(3)

    for writer in video_writers.values():
        writer.release()

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file reader example.")
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    parser.add_argument(
        "--output-path",
        type=str,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Path to the folder where converted data will be written. Default: {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument(
        "--camera-name", type=str, default="oak0", help="The name of the camera to visualize. Default: oak0."
    )
    parser.add_argument(
        "--disparity-scale", type=int, default=1, help="Scale for amplifying disparity color mapping. Default: 1."
    )
    args = parser.parse_args()

    main(Path(args.file_name), Path(args.output_path), args.camera_name, args.disparity_scale)
