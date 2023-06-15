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

import matplotlib.pyplot as plt
import numpy as np
from farm_ng.core.events_file_reader import EventsFileReader


def plot_image(images: list[np.ndarray], titles: list[str]) -> None:
    fig, axes = plt.subplots(1, len(images))
    for i, (image, title) in enumerate(zip(images, titles)):
        axes[i].imshow(image)
        axes[i].set_title(title)
        axes[i].axis("off")
    plt.show()


def main(file_name: str) -> None:
    # create the file reader
    reader = EventsFileReader(Path(file_name))
    assert reader.open()

    # reader the header
    header_log = reader.get_index()[0]
    header = header_log.read_message()
    labels, sublabels = header.labels, header.sublabels
    print(f"labels: {labels}")
    print(f"sublabels: {sublabels}")

    # the annotation files have first the image and later the annotation with masks
    image_log = reader.get_index()[1]
    annotations_log = reader.get_index()[2:]

    images_vis, titles_vis = [], []

    # visualize the image
    image = image_log.read_message()
    image_vis = np.frombuffer(image.data, dtype="uint8")
    image_vis = image_vis.reshape(image.layout.size.height, image.layout.size.width, 3)

    images_vis.append(image_vis)
    titles_vis.append("image")

    # visualize the annotation
    for annotation_log in annotations_log:
        annotations_set = annotation_log.read_message()
        annotations = annotations_set.annotations
        label, sublabel = annotations[0].label, annotations[0].sublabel
        mask_vis = np.frombuffer(annotations_set.mask.data, dtype="uint8") * 255
        mask_vis = mask_vis.reshape(annotations_set.mask.layout.size.height, annotations_set.mask.layout.size.width)
        win_name = f"mask-{label}-{sublabel}"
        titles_vis.append(win_name)
        images_vis.append(mask_vis)

    assert reader.close()

    plot_image(images_vis, titles_vis)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Event file reader example.")
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    args = parser.parse_args()
    main(args.file_name)
