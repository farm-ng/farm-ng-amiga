# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
# Copyright (c) farm-ng, inc. All rights reserved.
import argparse
from pathlib import Path
from typing import List

import cv2
import numpy as np
from farm_ng.core import event_pb2
from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.core.uri import uri_pb2
from farm_ng.oak import oak_pb2


def main(file_name: str) -> None:
    # create the file reader
    reader = EventsFileReader(Path(file_name))
    assert reader.open()

    # main window to visualize image
    uris: List[uri_pb2.Uri] = reader.uris()

    # choose the Uri stream to seek in file
    uri: uri_pb2.Uri = uris[1]

    num_events: int = reader.num_events(uri)
    current_event: int = 0

    while current_event < num_events - 1:
        # read frame by frame
        # get the event and offset
        event: event_pb2.Event
        offset: int
        event, offset = reader.get_event(uri, current_event)

        # seek and parse the message
        sample: oak_pb2.OakDataSample
        sample = reader.read_message(event, offset)
        frame: oak_pb2.OakSyncFrame = sample.frame

        # cast image data bytes to numpy and decode
        # NOTE: explore frame.[rgb, disparity, left, right]
        disparity = cv2.imdecode(np.frombuffer(frame.disparity.image_data, dtype="uint8"), cv2.IMREAD_GRAYSCALE)
        rgb = cv2.imdecode(np.frombuffer(frame.rgb.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)

        # visualize the image
        disparity_color = cv2.applyColorMap(disparity * 2, cv2.COLORMAP_HOT)

        rgb_window_name = "rgb:" + event.uri.query
        disparity_window_name = "depth:" + event.uri.query

        # we use opencv for convenience, use kivy, pangolin or you preferred viz tool :)
        cv2.namedWindow(disparity_window_name, cv2.WINDOW_NORMAL)
        cv2.namedWindow(rgb_window_name, cv2.WINDOW_NORMAL)

        cv2.imshow(disparity_window_name, disparity_color)
        cv2.imshow(rgb_window_name, rgb)
        cv2.waitKey(30)

        current_event += 1

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file reader example.")
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    args = parser.parse_args()
    main(args.file_name)
