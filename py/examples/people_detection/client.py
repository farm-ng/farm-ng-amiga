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
from typing import List

import grpc
import numpy as np
from farm_ng.people_detection import people_detection_pb2
from farm_ng.people_detection import people_detection_pb2_grpc
from farm_ng.service.service_client import ClientConfig


class PeopleDetectorClient:
    def __init__(self, config: ClientConfig) -> None:
        self.channel = grpc.aio.insecure_channel(f"{config.address}:{config.port}")
        self.stub = people_detection_pb2_grpc.PeopleDetectionServiceStub(self.channel)

    async def detect_people(self, image: np.ndarray, score_threshold: float) -> List[people_detection_pb2.Detection]:
        response = await self.stub.detectPeople(
            people_detection_pb2.DetectPeopleRequest(
                config=people_detection_pb2.DetectPeopleConfig(confidence_threshold=score_threshold),
                image=people_detection_pb2.Image(
                    data=image.tobytes(),
                    size=people_detection_pb2.ImageSize(width=image.shape[1], height=image.shape[0]),
                    num_channels=image.shape[2],
                    dtype="uint8",
                ),
            )
        )
        return list(response.detections)
