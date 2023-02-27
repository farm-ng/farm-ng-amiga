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
from typing import List

import cv2
import grpc
import numpy as np
from farm_ng.oak import oak_pb2
from farm_ng.oak.camera_client import OakCameraClient
from farm_ng.people_detection import people_detection_pb2
from farm_ng.people_detection import people_detection_pb2_grpc
from farm_ng.service.service_client import ClientConfig
from limbus.core import Component
from limbus.core import ComponentState
from limbus.core import InputParams
from limbus.core import OutputParams
from limbus.core.pipeline import Pipeline


class PeopleDetectorClient:
    def __init__(self, config: ClientConfig) -> None:
        self.channel = grpc.aio.insecure_channel(f"{config.address}:{config.port}")
        self.stub = people_detection_pb2_grpc.PeopleDetectionServiceStub(self.channel)

    async def detect_people(self, image: np.ndarray, score_threshold: float) -> List[people_detection_pb2.Detection]:
        response = await self.stub.detectPeople(
            people_detection_pb2.DetectPeopleRequest(
                config=people_detection_pb2.DetectPeopleConfig(confidence_threshold=score_threshold),
                image_size=people_detection_pb2.ImageSize(width=image.shape[1], height=image.shape[0]),
                image_data=image.tobytes(),
            )
        )
        return [d for d in response.detections]


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


class OpenCvCamera(Component):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        # configure the camera client
        self.grabber = cv2.VideoCapture(0)

    @staticmethod
    def register_outputs(outputs: OutputParams) -> None:
        outputs.declare("rgb", np.ndarray)

    async def forward(self):
        ret, frame = self.grabber.read()
        if not ret:
            return ComponentState.STOPPED

        await self.outputs.rgb.send(frame)

        return ComponentState.OK


class PeopleDetector(Component):
    def __init__(self, name: str, config: ClientConfig, confidence_threshold: float) -> None:
        super().__init__(name)
        self.confidence_threshold = confidence_threshold
        self.detector_client = PeopleDetectorClient(config)

    @staticmethod
    def register_inputs(inputs: InputParams) -> None:
        inputs.declare("rgb", np.ndarray)

    @staticmethod
    def register_outputs(outputs: OutputParams) -> None:
        outputs.declare("detections", List[people_detection_pb2.Detection])

    async def forward(self):
        # get the image
        image: np.ndarray = await self.inputs.rgb.receive()
        image_height, image_width = image.shape[:2]

        # send data to the server
        detections: List[people_detection_pb2.Detection] = await self.detector_client.detect_people(
            image, self.confidence_threshold
        )

        # send the detections
        await self.outputs.detections.send(detections)
        return ComponentState.OK


class Visualization(Component):
    @staticmethod
    def register_inputs(inputs: InputParams) -> None:
        inputs.declare("rgb", np.ndarray)
        inputs.declare("detections", List[people_detection_pb2.Detection])

    async def forward(self):
        image, detections = await asyncio.gather(self.inputs.rgb.receive(), self.inputs.detections.receive())

        image_vis = image.copy()
        for det in detections:
            image_vis = cv2.rectangle(
                image_vis, (int(det.x), int(det.y)), (int(det.x + det.width), int(det.y + det.height)), (0, 255, 0), 2
            )

        cv2.namedWindow("image", cv2.WINDOW_NORMAL)
        cv2.imshow("image", image_vis)
        cv2.waitKey(1)


async def main(config_camera: ClientConfig, config_detector: ClientConfig) -> None:

    # cam = AmigaCamera("amiga-camera", config_camera, stream_every_n=1)
    cam = OpenCvCamera("opencv-camera")
    detector = PeopleDetector("people-detector", config_detector, confidence_threshold=0.5)
    viz = Visualization("visualization")

    cam.outputs.rgb >> detector.inputs.rgb
    cam.outputs.rgb >> viz.inputs.rgb
    detector.outputs.detections >> viz.inputs.detections

    pipeline = Pipeline()
    pipeline.add_nodes([cam, detector, viz])

    await pipeline.async_run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-people-detector")
    parser.add_argument("--port-camera", type=int, required=True, help="The camera port.")
    parser.add_argument("--address-camera", type=str, default="localhost", help="The camera address")
    parser.add_argument("--port-detector", type=int, required=True, help="The camera port.")
    parser.add_argument("--address-detector", type=str, default="localhost", help="The camera address")
    parser.add_argument("--stream-every-n", type=int, default=1, help="Streaming frequency")
    args = parser.parse_args()

    # create the config for the clients
    config_camera = ClientConfig(port=args.port_camera, address=args.address_camera)
    config_camera.stream_every_n = args.stream_every_n

    config_detector = ClientConfig(port=args.port_detector, address=args.address_detector)

    # run the main
    asyncio.run(main(config_camera, config_detector))
