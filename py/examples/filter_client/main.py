"""Example of a state estimation filter service client."""
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

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics
from farm_ng.filter.filter_pb2 import DivergenceCriteria
from farm_ng_core_pybind import Pose3F64


async def main(service_config_path: Path) -> None:
    """Run the filter service client.

    Args:
        service_config_path (Path): The path to the filter service config.
    """
    # create a client to the filter service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        # Find the monotonic service send timestamp (this is the time the filter calculated the state),
        # or the first timestamp if not available.
        stamp = (
            get_stamp_by_semantics_and_clock_type(event, StampSemantics.SERVICE_SEND, "monotonic")
            or event.timestamps[0].stamp
        )

        # Unpack the filter state message
        pose: Pose3F64 = Pose3F64.from_proto(message.pose)
        orientation: float = message.heading
        uncertainties: list[float] = [message.uncertainty_diagonal.data[i] for i in range(3)]
        divergence_criteria: list[DivergenceCriteria] = [
            DivergenceCriteria.Name(criteria) for criteria in message.divergence_criteria
        ]

        # Print some key details about the filter state
        print("\n###################")
        print(f"Timestamp: {stamp}")
        print("Filter state received with pose:")
        print(f"x: {pose.translation[0]:.3f} m, y: {pose.translation[1]:.3f} m, orientation: {orientation:.3f} rad")
        print(f"Parent frame: {pose.frame_a} -> Child frame: {pose.frame_b}")
        print(f"Filter has converged: {message.has_converged}")
        print("Pose uncertainties:")
        print(f"x: {uncertainties[0]:.3f} m, y: {uncertainties[1]:.3f} m, orientation: {uncertainties[2]:.3f} rad")
        if not message.has_converged:
            print(f"Filter diverged due to: {divergence_criteria}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga filter stream example.")
    parser.add_argument("--service-config", type=Path, required=True, help="The filter service config.")
    args = parser.parse_args()

    asyncio.run(main(args.service_config))
