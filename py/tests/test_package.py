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
import farm_ng
from farm_ng.amiga import amiga_pb2
from farm_ng.canbus import canbus_pb2
from farm_ng.gps import gps_pb2
from farm_ng.imu import imu_pb2
from farm_ng.oak import oak_pb2


def test_import() -> None:
    assert farm_ng.core is not None
    assert farm_ng.core.__version__ is not None
    assert farm_ng.oak is not None
    assert farm_ng.oak.__version__ is not None
    assert farm_ng.imu is not None
    assert farm_ng.imu.__version__ is not None
    assert farm_ng.canbus is not None
    assert farm_ng.canbus.__version__ is not None
    assert farm_ng.amiga is not None
    assert farm_ng.amiga.__version__ is not None

    assert canbus_pb2 is not None
    assert oak_pb2 is not None
    assert imu_pb2 is not None
    assert gps_pb2 is not None
    assert amiga_pb2 is not None
