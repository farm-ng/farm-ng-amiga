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
from pathlib import Path
from typing import List

import cv2
import numpy as np
from farm_ng.core import event_pb2
from farm_ng.core.events_file_reader import EventLogPosition
from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.oak import oak_pb2


# helper function to filter valid events given a message type
def event_has_message(event: event_pb2.Event, msg_type) -> bool:
    return event.uri.query.split("&")[0].split(".")[-1] == msg_type.__name__


def main(file_name: str, camera_name: str) -> None:
    # create the file reader
    reader = EventsFileReader(Path(file_name))
    assert reader.open()

    # filter the events containing `oak_pb2.OakDataSample`
    events: List[EventLogPosition] = [
        x for x in reader.get_index() if event_has_message(x.event, oak_pb2.OakDataSample)
    ]

    # filter the image based events by camera name
    cam_events: List[EventLogPosition] = [x for x in events if x.event.uri.path == f"{camera_name}/video"]

    for event_log in cam_events:
        # parse the message
        sample: oak_pb2.OakDataSample
        sample = event_log.read_message()

        frame: oak_pb2.OakSyncFrame = sample.frame
        for view in ["rgb", "disparity", "left", "right"]:
            img = cv2.imdecode(np.frombuffer(getattr(frame, view).image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)
            if view == "disparity":
                img = cv2.applyColorMap(img * 2, cv2.COLORMAP_HOT)

            window_name: str = view + ":" + event_log.event.uri.query
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.imshow(window_name, img)

        cv2.waitKey(3)

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file reader example.")
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    parser.add_argument(
        "--camera-name", type=str, default="oak0", help="The name of the camera to visualize. Default: oak0."
    )
    args = parser.parse_args()
    main(args.file_name, args.camera_name)
