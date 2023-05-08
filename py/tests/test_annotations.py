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
import numpy as np
import torch

from farm_ng.annotations import annotations_pb2


def make_point(x: float, y: float) -> annotations_pb2.Point2d:
    return annotations_pb2.Point2d(x=x, y=y)


class TestAnnotations:
    def test_smoke(self) -> None:
        # generate a mask
        mask = torch.tensor([[0, True, 0], [True, 0, True]])

        annotation = annotations_pb2.Annotation(
            label="person",
            sublabel="positive",
            points=[make_point(x, y) for y, x in mask.nonzero()],
            width=1,
            mask=annotations_pb2.ImageMask(
                data=mask.byte().numpy().tobytes(),
                size=annotations_pb2.ImageSize(width=mask.shape[1], height=mask.shape[0])
            )
        )

        assert annotation.label == "person"
        assert annotation.sublabel == "positive"
        assert annotation.points == [make_point(1, 0), make_point(0, 1), make_point(2, 1)]
        assert annotation.width == 1

        # reconstruct the mask
        mask_hat = torch.frombuffer(bytearray(annotation.mask.data), dtype=torch.bool)
        mask_hat = mask_hat.reshape(
            annotation.mask.size.height, annotation.mask.size.width)
        
        assert (mask == mask_hat).all()



