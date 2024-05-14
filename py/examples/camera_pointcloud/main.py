"""Example of computing a point cloud from the camera feed."""
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
from pathlib import Path

import kornia as K
import torch
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.uri import uri_pb2
from farm_ng.oak import oak_pb2
from google.protobuf.empty_pb2 import Empty
from kornia.core import Tensor
from kornia.core import tensor
from kornia_rs import ImageDecoder


def decode_disparity(message: oak_pb2.OakFrame, decoder: ImageDecoder) -> Tensor:
    """Decode the disparity image from the message.

    Args:
        message (oak_pb2.OakFrame): The camera frame message.
        decoder (ImageDecoder): The image decoder.

    Returns:
        Tensor: The disparity image tensor (HxW).
    """
    # decode the disparity image from the message into a dlpack tensor for zero-copy
    disparity_dl = decoder.decode(message.image_data)

    # cast the dlpack tensor to a torch tensor
    disparity_t = torch.from_dlpack(disparity_dl)

    return disparity_t[..., 0].float()  # HxW


def get_camera_matrix(camera_data: oak_pb2.CameraData) -> Tensor:
    """Compute the camera matrix from the camera calibration data.

    Args:
        camera_data (oak_pb2.CameraData): The camera calibration data.

    Returns:
        Tensor: The camera matrix with shape 3x3.
    """
    fx = camera_data.intrinsic_matrix[0]
    fy = camera_data.intrinsic_matrix[4]
    cx = camera_data.intrinsic_matrix[2]
    cy = camera_data.intrinsic_matrix[5]

    return tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])


async def main() -> None:
    """Request the camera calibration from the camera service.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-pointcloud example.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    parser.add_argument("--save-disparity", action="store_true", help="Save the disparity image.")
    parser.add_argument("--save-pointcloud", action="store_true", help="Save the depth image.")
    args = parser.parse_args()

    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(args.service_config, EventServiceConfig())

    camera_client = EventClient(config)

    # get the calibration message
    calibration_proto: oak_pb2.OakCalibration = await camera_client.request_reply("/calibration", Empty(), decode=True)

    # NOTE: The OakCalibration message contains the camera calibration data for all the cameras.
    # Since we are interested in the disparity image, we will use the calibration data for the right camera
    # which is the first camera in the list.
    camera_data: oak_pb2.CameraData = calibration_proto.camera_data[0]

    # compute the camera matrix from the calibration data
    camera_matrix: Tensor = get_camera_matrix(camera_data)

    image_decoder = ImageDecoder()

    # stream the disparity image
    async for event, message in camera_client.subscribe(
        SubscribeRequest(uri=uri_pb2.Uri(path="oak/1/disparity"), every_n=5), decode=True
    ):
        # cast image data bytes to a tensor and decode
        disparity_t = decode_disparity(message, image_decoder)  # HxW

        # compute the depth image from the disparity image
        calibration_baseline: float = 0.075  # m
        calibration_focal: float = float(camera_matrix[0, 0])

        depth_t = K.geometry.depth.depth_from_disparity(
            disparity_t, baseline=calibration_baseline, focal=calibration_focal
        )  # HxW

        # compute the point cloud from the depth image
        points_xyz = K.geometry.depth.depth_to_3d_v2(depth_t, camera_matrix)  # HxWx3

        # filter out points that are in the range of the camera
        valid_mask = (points_xyz[..., -1:] >= 0.2) & (points_xyz[..., -1:] <= 7.5)  # HxWx1
        valid_mask = valid_mask.repeat(1, 1, 3)  # HxWx3

        points_xyz = points_xyz[valid_mask].reshape(-1, 3)  # Nx3

        # serialize the disparity image
        if args.save_disparity:
            K.io.write_image(
                f"disparity_{message.meta.sequence_num}.jpg", disparity_t[None].repeat(3, 1, 1).mul(255).byte()
            )

        # serialize the pointcloud
        if args.save_pointcloud:
            print(f"Saving point cloud to pointcloud_{message.meta.sequence_num}.ply ...")

            K.utils.save_pointcloud_ply(f"pointcloud_{message.meta.sequence_num}.ply", points_xyz)

            print(f"Saving point cloud to pointcloud_{message.meta.sequence_num}.ply ... OK")


if __name__ == "__main__":
    asyncio.run(main())
