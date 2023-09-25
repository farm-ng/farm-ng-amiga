"""Example of how to read an events file and convert it to a video."""
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
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from farm_ng.core.events_file_reader import EventLogPosition
from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.oak import oak_pb2
from kornia_rs import ImageDecoder
from tqdm import tqdm


# TODO: add to farm_ng.core
def build_events_dict(events_index: list[EventLogPosition]) -> dict[str, list[EventLogPosition]]:
    """Build a dictionary of lists of events, where the key is the path of the event.

    Args:
        events_index (list[EventLogPosition]): [description]

    Returns:
        dict[str, list[EventLogPosition]]: [description]
    """
    events_dict: dict[str, list[EventLogPosition]] = defaultdict(list)
    for event_index in events_index:
        # NOTE: this is how we get the service name from the event uri
        # TODO: this should be done by the event service
        service_name = event_index.event.uri.query.split("&")[-1].split("=")[-1]
        topic_name = f"/{service_name}{event_index.event.uri.path}"
        events_dict[topic_name].append(event_index)
    return events_dict


def main(
    file_name: Path, output_path: Path, camera_name: str, view_name: str, disparity_scale: int, video_to_jpg: bool
) -> None:
    """Read an events file and convert it to a video.

    Args:

        file_name (Path): The path to the events file.
        output_path (Path): The path to the folder where the converted data will be written.
        camera_name (str): The name of the camera to visualize.
        view_name (str): The name of the view to visualize.
        disparity_scale (int, optional): The scale to apply to the disparity image. Defaults to 1.
        video_to_jpg (bool, optional): Whether to convert the video to jpgs. Defaults to False.
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

    # create a video writer to write the video
    video_writer: cv2.VideoWriter | None = None

    # instantiate the image decoder
    image_decoder = ImageDecoder()

    event_log: EventLogPosition
    for event_log in tqdm(camera_events):
        # parse the message
        sample: oak_pb2.OakFrame = event_log.read_message()

        # decode image
        img: np.ndarray = np.from_dlpack(image_decoder.decode(sample.image_data))

        if view_name == "disparity":
            disparity_scale: int = max(1, int(disparity_scale))
            img = cv2.applyColorMap(img * disparity_scale, cv2.COLORMAP_HOT)

        # show image
        cv2.imshow(topic_name, img)

        if not video_to_jpg:
            # create the video writer if it doesn't exist
            if video_writer is None:
                height, width, _ = img.shape
                file_path = file_name.parent if not output_path else output_path.absolute()
                video_name = file_path / (file_name.stem + f".{view_name}.mp4")
                video_writer = cv2.VideoWriter(str(video_name), cv2.VideoWriter_fourcc(*'mp4v'), 10, (width, height))

            # write the frame to the video
            video_writer.write(img)
        else:
            # write frame to jpg
            file_path = file_name.parent if not output_path else output_path.absolute()
            file_path = file_path / file_name.stem / f"{view_name}"
            frame_name: str = f"frame_{sample.meta.sequence_num:06d}.jpg"
            if not file_path.exists():
                file_path.mkdir(parents=True, exist_ok=True)

            # write the frame to the path
            cv2.imwrite(str(file_path / frame_name), img)

        cv2.waitKey(1)

    # close the video writer and the file reader
    video_writer.release()
    reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file converter example.")
    parser.add_argument("--file-name", type=Path, required=True, help="Path to the `events.bin` file.")
    parser.add_argument("--output-path", type=Path, help="Path to the folder where converted data will be written.")
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
    parser.add_argument(
        "--disparity-scale", type=int, default=1, help="Scale for amplifying disparity color mapping. Default: 1."
    )
    parser.add_argument(
        '--video-to-jpg',
        action='store_true',
        help="Use this flag to convert video .bin files to a series of jpg images. Default is mp4.",
    )
    args = parser.parse_args()

    main(args.file_name, args.output_path, args.camera_name, args.view_name, args.disparity_scale, args.video_to_jpg)
