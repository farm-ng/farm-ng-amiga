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

from farm_ng.canbus import amiga_v6_pb2
from farm_ng.canbus.packet import DASHBOARD_NODE_ID
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file


async def main(service_config_path: Path, store: bool) -> None:
    """Run the canbus service client.

    Args:
        service_config_path (Path): The path to the canbus service config.
    """

    vmax_read_req = amiga_v6_pb2.ConfigRequestReply(
        node_id=DASHBOARD_NODE_ID,
        op_id=amiga_v6_pb2.ConfigOperationIds.READ,
        val_id=amiga_v6_pb2.ConfigValueIds.VEL_MAX,
        unit=amiga_v6_pb2.ConfigValueUnits.MPS,
    )

    vmax_write_req = amiga_v6_pb2.ConfigRequestReply(
        node_id=DASHBOARD_NODE_ID,
        op_id=amiga_v6_pb2.ConfigOperationIds.WRITE,
        val_id=amiga_v6_pb2.ConfigValueIds.VEL_MAX,
        unit=amiga_v6_pb2.ConfigValueUnits.MPS,
        double_value=0.254,
    )

    track_read_req = amiga_v6_pb2.ConfigRequestReply(
        node_id=DASHBOARD_NODE_ID,
        op_id=amiga_v6_pb2.ConfigOperationIds.READ,
        val_id=amiga_v6_pb2.ConfigValueIds.WHEEL_TRACK,
        unit=amiga_v6_pb2.ConfigValueUnits.METERS,
    )

    track_write_req = amiga_v6_pb2.ConfigRequestReply(
        node_id=DASHBOARD_NODE_ID,
        op_id=amiga_v6_pb2.ConfigOperationIds.WRITE,
        val_id=amiga_v6_pb2.ConfigValueIds.WHEEL_TRACK,
        unit=amiga_v6_pb2.ConfigValueUnits.METERS,
        double_value=0.8,
    )

    store_req = amiga_v6_pb2.ConfigRequestReply(node_id=DASHBOARD_NODE_ID, op_id=amiga_v6_pb2.ConfigOperationIds.STORE)

    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    # Read and write the VEL_MAX parameter.
    for req in [vmax_read_req, vmax_write_req, vmax_read_req]:
        print("###################")
        print(f"Request:\n{req}\n")
        res = await EventClient(config).request_reply("/config_request", req, decode=True)
        print(f"Response:\n{res}\n")

    # Read and write the WHEEL_TRACK parameter.
    for req in [track_read_req, track_write_req, track_read_req]:
        print("###################")
        print(f"Request:\n{req}\n")
        res = await EventClient(config).request_reply("/config_request", req, decode=True)
        print(f"Response:\n{res}\n")

    # Optionally, store the parameters.
    if store:
        print("###################")
        print(f"Request:\n{store_req}\n")
        res = await EventClient(config).request_reply("/config_request", store_req, decode=True)
        print(f"Response:\n{res}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Query / set dashboard config parameters.")
    parser.add_argument("--service-config", type=Path, required=True, help="The canbus service config.")
    parser.add_argument("--store", action="store_true", help="Store the persistent parameters on the dashboard.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config, args.store))
