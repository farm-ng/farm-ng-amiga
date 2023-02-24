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
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2
import numpy as np
from farm_ng.oak import oak_pb2
from farm_ng.oak.camera_client import OakCameraClient
from farm_ng.service.service_client import ClientConfig
from limbus.core import Component
from limbus.core import ComponentState
from limbus.core import InputParams
from limbus.core import OutputParams
from limbus.core.pipeline import Pipeline


@dataclass
class Detection:
    x: int
    y: int
    w: int
    h: int
    confidence: float


class AmigaCamera(Component):
    def __init__(self, name: str, address: str, port: int, stream_every_n: int) -> None:
        super().__init__(name)
        # configure the camera client
        self.config = ClientConfig(address=address, port=port)
        self.client = OakCameraClient(self.config)

        # create a stream
        self.stream = self.client.stream_frames(every_n=stream_every_n)

    @staticmethod
    def register_outputs(outputs: OutputParams) -> None:
        outputs.declare("rgb", np.ndarray)

    def _decode_image(self, image_data: bytes) -> np.ndarray:
        image: np.ndarray = np.frombuffer(image_data, dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_UNCHANGED)
        return image

    async def forward(self):
        response = await self.stream.read()
        frame: oak_pb2.OakSyncFrame = response.frame

        await self.outputs.rgb.send(self._decode_image(frame.rgb.image_data))

        return ComponentState.OK


class PeopleDetector(Component):
    def __init__(self, name: str, models_dir: Path, score_thershold: float) -> None:
        super().__init__(name)
        self.score_threshold = score_thershold
        self.model = cv2.dnn.readNetFromTensorflow(
            str(models_dir / "frozen_inference_graph.pb"), str(models_dir / "ssd_mobilenet_v2_coco_2018_03_29.pbtxt")
        )

    @staticmethod
    def register_inputs(inputs: InputParams) -> None:
        inputs.declare("rgb", np.ndarray)

    @staticmethod
    def register_outputs(outputs: OutputParams) -> None:
        outputs.declare("detections", list[Detection])

    async def forward(self):
        # get the image
        image: np.ndarray = await self.inputs.rgb.receive()
        image_height, image_width = image.shape[:2]

        # run the model
        self.model.setInput(cv2.dnn.blobFromImage(image, size=(300, 300), swapRB=True))
        output = self.model.forward()

        # postprocess the output
        detections: List[Detection] = []
        for detection in output[0, 0, :, :]:
            class_id = detection[1]
            if class_id != 1:  # person
                continue
            score = float(detection[2])
            if score > self.score_threshold:
                left = detection[3] * image_width
                top = detection[4] * image_height
                right = detection[5] * image_width
                bottom = detection[6] * image_height
                detections.append(Detection(left, top, right - left, bottom - top, score))

        # send the detections
        await self.outputs.detections.send(detections)
        return ComponentState.OK


class Visualization(Component):
    @staticmethod
    def register_inputs(inputs: InputParams) -> None:
        inputs.declare("rgb", np.ndarray)
        inputs.declare("detections", List[Detection])

    async def forward(self):
        image, detections = await asyncio.gather(self.inputs.rgb.receive(), self.inputs.detections.receive())

        image_vis = image.copy()
        for det in detections:
            image_vis = cv2.rectangle(
                image_vis, (int(det.x), int(det.y)), (int(det.x + det.w), int(det.y + det.h)), (0, 255, 0), 2
            )

        cv2.namedWindow("image", cv2.WINDOW_NORMAL)
        cv2.imshow("image", image_vis)
        cv2.waitKey(1)


async def main(address: str, port: int, stream_every_n: int, models_dir: Path) -> None:

    cam = AmigaCamera("amiga-camera", address, port, stream_every_n)
    detector = PeopleDetector("people-detector", models_dir, score_thershold=0.5)
    viz = Visualization("visualization")

    cam.outputs.rgb >> detector.inputs.rgb
    cam.outputs.rgb >> viz.inputs.rgb
    detector.outputs.detections >> viz.inputs.detections

    pipeline = Pipeline()
    pipeline.add_nodes([cam, detector, viz])

    await pipeline.async_run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-people-detector")
    parser.add_argument("--port", type=int, required=True, help="The camera port.")
    parser.add_argument("--address", type=str, default="localhost", help="The camera address")
    parser.add_argument("--stream-every-n", type=int, default=1, help="Streaming frequency")
    parser.add_argument("--models-dir", type=str, required=True, help="The path to the models directory")
    args = parser.parse_args()

    models_path = Path(args.models_dir).absolute()
    assert models_path.exists(), f"Models directory {models_path} does not exist."

    asyncio.run(main(args.address, args.port, args.stream_every_n, models_path))
