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
import logging
from pathlib import Path

import cv2
import grpc
import numpy as np
from farm_ng.people_detection import people_detection_pb2
from farm_ng.people_detection import people_detection_pb2_grpc


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PeopleDetectionService(people_detection_pb2_grpc.PeopleDetectionServiceServicer):
    def __init__(self, models_dir: Path) -> None:
        # load the model to detect people
        self.model = cv2.dnn.readNetFromTensorflow(
            str(models_dir / "frozen_inference_graph.pb"), str(models_dir / "ssd_mobilenet_v2_coco_2018_03_29.pbtxt")
        )
        logger.info("Loaded model: %s", models_dir.absolute())

    async def detectPeople(
        self, request: people_detection_pb2.DetectPeopleRequest, context: grpc.aio.ServicerContext
    ) -> people_detection_pb2.DetectPeopleReply:
        # decode the image
        image: np.ndarray = np.frombuffer(request.image_data, dtype="uint8")
        image = np.reshape(image, (request.image_size.height, request.image_size.width, 3))

        logger.debug("Detecting people in image of size %s", image.shape)

        # detect people
        self.model.setInput(cv2.dnn.blobFromImage(image, size=(300, 300), swapRB=True))
        detections = self.model.forward()

        logger.debug("Num detections %d", detections.shape[2])

        # create the reply
        response = people_detection_pb2.DetectPeopleReply()

        for i in range(detections.shape[2]):
            class_id = int(detections[0, 0, i, 1])
            if class_id != 1:  # 1 is the class id for person
                continue
            confidence: float = detections[0, 0, i, 2]
            if confidence > request.config.confidence_threshold:
                x = int(detections[0, 0, i, 3] * request.image_size.width)
                y = int(detections[0, 0, i, 4] * request.image_size.height)
                w = int(detections[0, 0, i, 5] * request.image_size.width) - x
                h = int(detections[0, 0, i, 6] * request.image_size.height) - y
                response.detections.append(
                    people_detection_pb2.Detection(x=x, y=y, width=w, height=h, confidence=confidence)
                )

        logger.debug("Num detections filtered %d", len(response.detections))

        return response


async def serve(port: int, models_dir: Path) -> None:
    server = grpc.aio.server()
    people_detection_pb2_grpc.add_PeopleDetectionServiceServicer_to_server(PeopleDetectionService(models_dir), server)
    server.add_insecure_port(f"[::]:{port}")

    logger.info("Starting server on port %i", port)
    await server.start()

    logger.info("Server started")
    await server.wait_for_termination()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="amiga-people-detector-service")
    parser.add_argument("--port", type=int, required=True, help="The camera port.")
    parser.add_argument("--models-dir", type=str, required=True, help="The path to the models directory")
    args = parser.parse_args()

    models_path = Path(args.models_dir).absolute()
    assert models_path.exists(), f"Models directory {models_path} does not exist."

    asyncio.run(serve(args.port, models_path))
