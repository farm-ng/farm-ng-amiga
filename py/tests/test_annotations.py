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
import pytest
import numpy as np

from farm_ng.annotations import annotations_pb2
from sophus import image_pb2, linalg_pb2


def make_point(x: float, y: float) -> linalg_pb2.Vec2F32:
    return linalg_pb2.Vec2F32(x=x, y=y)


@pytest.mark.skip(reason="enable if you have the latest sophus with DynImage")
class TestAnnotations:
    def test_smoke(self) -> None:
        # generate a mask
        mask = np.array([[0, 255, 0], [255, 0, 255]], dtype=np.uint8)
        points_pb = [make_point(1, 0), make_point(0, 1), make_point(2, 1)]
        height, width = mask.shape

        mask_pb = image_pb2.DynImage(
            data=mask.tobytes(),
            layout=image_pb2.ImageLayout(
                size=image_pb2.ImageSize(width=width, height=height),
                pitch_bytes=width * mask.dtype.itemsize,
            ),
            pixel_format=image_pb2.PixelFormat(
                number_type="unsigned",
                num_components=1,
                num_bytes_per_component=1,
            ),
        )

        annotation = annotations_pb2.Annotation(
            label="person",
            sublabel="positive",
            points=points_pb,
            width=1,
        )
        assert annotation.label == "person"
        assert annotation.sublabel == "positive"
        assert annotation.points == points_pb
        assert annotation.width == 1

        annotations_set = annotations_pb2.AnnotationsSet(
            frame_descriptor="events_0000000000000000_oak0_00000",
            label="person",
            sublabel="positive",
            annotations=[annotation],
            mask=mask_pb,
        )
        assert annotations_set.frame_descriptor == "events_0000000000000000_oak0_00000"
        assert annotations_set.label == "person"
        assert annotations_set.sublabel == "positive"
        assert annotations_set.annotations == [annotation]
        assert annotations_set.mask == mask_pb

        # reconstruct the mask
        mask_hat = np.frombuffer(bytearray(annotations_set.mask.data), dtype=np.uint8)
        mask_hat = mask_hat.reshape(
            annotations_set.mask.layout.size.height, annotations_set.mask.layout.size.width)
        
        assert np.allclose(mask, mask_hat)



