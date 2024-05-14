"""Example of a camera ArUco detector."""
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
import asyncio
from pathlib import Path

import cv2
import numpy as np
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.oak import oak_pb2
from google.protobuf.empty_pb2 import Empty


class ArucoDetector:
    """A class for detecting ArUco markers in an image frame."""

    def __init__(self, aruco_dict_type: str, marker_size: float) -> None:
        """Initialize the ArUco detector.

        Args:
            aruco_dict_type (str): The ArUco dictionary type.
            marker_size (float): The size of the ArUco marker in meters.
        """
        self._detector = self._create_detector(aruco_dict_type)
        self._marker_size = marker_size

    def _create_detector(self, aruco_dict_type: str) -> cv2.aruco.ArucoDetector:
        """Create an ArUco detector.

        Args:
            aruco_dict_type (str): The ArUco dictionary type.

        Returns:
            cv2.aruco.ArucoDetector: The ArUco detector.
        """
        aruco_params = cv2.aruco.DetectorParameters()

        # See all the available ArUco dictionary types here:
        # https://docs.opencv.org/4.x/de/d67/group__objdetect__aruco.html#ga4e13135a118f497c6172311d601ce00d
        aruco_dict = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, aruco_dict_type))
        return cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    def _create_object_points(self, marker_size: float) -> np.ndarray:
        """Create the object points for the ArUco markers.

        Args:
            marker_size (float): The size of the ArUco marker in meters.

        Returns:
            np.ndarray: The object points for the ArUco markers.
        """
        size_half: float = marker_size / 2.0
        return np.array(
            [
                [-size_half, -size_half, 0],
                [size_half, -size_half, 0],
                [size_half, size_half, 0],
                [-size_half, size_half, 0],
            ],
            dtype=np.float32,
        )

    @staticmethod
    def get_camera_matrix(camera_data: oak_pb2.CameraData) -> np.ndarray:
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

        return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])

    def detect_pose(self, frame: np.ndarray, camera_matrix: np.ndarray, distortion_coeff: np.ndarray):
        """Detect ArUco markers in an image frame.

        Args:
            frame (np.ndarray): The image frame in rgb format with shape HxWx3.
            camera_matrix (np.ndarray): The camera matrix with shape 3x3.
            distortion_coeff (np.ndarray): The distortion coefficients with shape 1x5.

        Returns:
            list: A list of ArUco marker detections with shape Nx4x3 and the frame with the detections drawn on it.
        """
        assert len(frame.shape) == 3 and frame.shape[2] == 3, "image must be rgb"

        # Convert the image to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        # Detect the markers
        corners, _, _ = self._detector.detectMarkers(gray)

        print(f"Detected {len(corners)} markers")

        rvec = []
        tvec = []
        frame_vis = frame

        for corner in corners:
            # Estimate the pose of the marker
            _rvec, _tvec, _ = cv2.aruco.estimatePoseSingleMarkers(
                corner, self._marker_size, camera_matrix, distortion_coeff
            )

            # store the results
            rvec.append(_rvec)
            tvec.append(_tvec)

            # Draw the detected marker and its pose
            frame_vis = cv2.drawFrameAxes(frame, camera_matrix, distortion_coeff, _rvec, _tvec, self._marker_size * 0.5)

        # Draw the detected markers
        frame_vis = cv2.aruco.drawDetectedMarkers(frame_vis, corners)

        return (np.array(rvec), np.array(tvec)), frame_vis


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera aruco-detector example.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    parser.add_argument("--aruco-type", type=str, default="DICT_6X6_250", help="The ArUco dictionary type.")
    parser.add_argument("--marker-size", type=float, default=0.0145, help="The size of the ArUco marker in meters.")
    args = parser.parse_args()

    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(args.service_config, EventServiceConfig())

    # create the camera client
    camera_client = EventClient(config)

    # request the camera calibration data
    calibration: oak_pb2.OakCalibration = await camera_client.request_reply("/calibration", Empty(), decode=True)

    # create the ArUco detector
    detector = ArucoDetector(aruco_dict_type=args.aruco_type, marker_size=args.marker_size)

    # NOTE: The OakCalibration message contains the camera calibration data for all the cameras.
    # Since we are interested in the disparity image, we will use the calibration data for the right camera
    # which is the first camera in the list.
    camera_matrix: np.ndarray = detector.get_camera_matrix(calibration.camera_data[0])
    distortion_coeff = np.array(calibration.camera_data[0].distortion_coeff)

    async for event, message in camera_client.subscribe(config.subscriptions[0], decode=True):
        # cast image data bytes to numpy and decode
        image: np.ndarray = cv2.imdecode(np.frombuffer(message.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)

        # detect the aruco markers in the image
        # NOTE: do something with the detections here, e.g. publish them to the event service
        detections, image_vis = detector.detect_pose(image, camera_matrix, distortion_coeff)

        # visualize the image
        cv2.namedWindow("image", cv2.WINDOW_NORMAL)
        cv2.imshow("image", image_vis)
        cv2.waitKey(1)


if __name__ == "__main__":
    asyncio.run(main())
