"""Example of reading events from an events file."""
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
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from farm_ng.core.events_file_reader import EventLogPosition
from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.oak import oak_pb2
from utils import build_events_dict


def main(file_name: Path, camera_name: str, view_name: str) -> None:
    """Reads an events file and displays the images from the specified camera and view.

    Args:
        file_name (Path): The path to the events file.
        camera_name (str): The name of the camera to visualize.
        view_name (str): The name of the camera view to visualize.
    """
    # create the file reader
    reader = EventsFileReader(file_name)
    success: bool = reader.open()
    if not success:
        raise RuntimeError(f"Failed to open events file: {file_name}")

    # get the index of the events file
    events_index: list[EventLogPosition] = reader.get_index()

    # structure the index as a dictionary of lists of events
    events_dict: dict[str, list[EventLogPosition]] = build_events_dict(events_index)

    print("All available topics:")
    print(events_dict.keys())

    # customize camera and view
    topic_name = f"/{camera_name}/{view_name}"
    if topic_name not in events_dict:
        raise RuntimeError(f"Camera view not found: {topic_name}")

    camera_events: list[EventLogPosition] = events_dict[topic_name]

    cv2.namedWindow(topic_name, cv2.WINDOW_NORMAL)

    event_log: EventLogPosition
    for event_log in camera_events:

        # parse the message
        sample: oak_pb2.OakFrame = event_log.read_message()

        # decode image
        img: np.ndarray = cv2.imdecode(np.frombuffer(sample.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)

        # show image
        cv2.imshow(topic_name, img)
        cv2.setWindowTitle(topic_name, f"{topic_name} - {int(event_log.event.timestamps[-2].stamp * 1e9)}")
        cv2.waitKey(250)  # to slow down the playback

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file reader example.")
    parser.add_argument("--file-name", type=Path, required=True, help="Path to the `events.bin` file.")
    parser.add_argument(
        "--camera-name", type=str, default="oak0", help="The name of the camera to visualize. Default: oak0."
    )
    parser.add_argument(
        "--view-name",
        type=str,
        default="rgb",
        choices=["rgb", "left", "right", "disparity"],
        help="The name of the camera view to visualize. Default: rbg.",
    )
    args = parser.parse_args()
    main(args.file_name, args.camera_name, args.view_name)
