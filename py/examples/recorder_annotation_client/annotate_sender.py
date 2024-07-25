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
import time
from pathlib import Path

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.recorder_pb2 import AnnotationKind
from farm_ng.core.recorder_pb2 import RecorderAnnotation
from farm_ng.core.timestamp_pb2 import Timestamp


async def main(service_config_path: Path) -> None:
    """Run the camera service client.

    Args:
        service_config_path (Path): The path to the camera service config.
    """
    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    stamp = Timestamp()
    stamp.stamp = time.monotonic()
    stamp.clock_name = "boron-banana/monotonic"
    stamp.semantics = "client/send"

    msg = RecorderAnnotation()
    msg.kind = AnnotationKind.NOTE
    msg.message = "Fuck from Gui"
    msg.stamp.CopyFrom(stamp)

    await EventClient(config).request_reply("data_collection/annotate", msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Stream motor states from the canbus service.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
