"""Example of subscribing to events from multiple clients."""
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
from farm_ng.core.event_pb2 import Event
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics


class GeoTaggedImageSubscriber:
    """Example of subscribing to events from multiple clients."""

    def __init__(self, service_config: EventServiceConfigList, time_delta: float) -> None:
        """Initialize the multi-client subscriber.

        Args:
            service_config: The service config.
            time_delta: The time delta threshold.
        """
        self.service_config = service_config
        self.time_delta = time_delta

        self.clients: dict[str, EventClient] = {}
        self.subscriptions: list[SubscribeRequest] = []

        # populate the clients
        config: EventServiceConfig
        for config in self.service_config.configs:
            if not config.port:
                self.subscriptions = list(config.subscriptions)
                continue
            self.clients[config.name] = EventClient(config)

        # create a queue to store the images since they come in faster than we can process them
        self.image_queue: asyncio.Queue = asyncio.Queue()

    async def _subscribe(self, subscription: SubscribeRequest) -> None:
        # the client name is the last part of the query
        client_name: str = subscription.uri.query.split("=")[-1]
        client: EventClient = self.clients[client_name]
        # subscribe to the event
        async for event, message in client.subscribe(subscription, decode=False):
            print(f"Received event from {client_name}{event.uri.path}")
            if "OakFrame" in event.uri.query:
                await self.image_queue.put((event, message))
            elif "GpsFrame" in event.uri.query:
                stamp_gps = get_stamp_by_semantics_and_clock_type(
                    event, semantics=StampSemantics.SERVICE_SEND, clock_type="monotonic"
                )
                if stamp_gps is None:
                    continue

                geo_image: tuple[tuple[Event, bytes], ...] | None = None

                while self.image_queue.qsize() > 0:
                    event_image, image = await self.image_queue.get()
                    stamp_image = get_stamp_by_semantics_and_clock_type(
                        event_image, semantics=StampSemantics.SERVICE_SEND, clock_type="monotonic"
                    )
                    if stamp_image is None:
                        continue

                    stamp_diff: float = abs(stamp_gps - stamp_image)

                    if stamp_diff > self.time_delta:
                        print(f"Skipping image because stamp_diff is too large: {stamp_diff}")
                        continue
                    else:
                        print(f"Synced image and gps data with stamp_diff: {stamp_diff}")
                        # NOTE: explore expanding this as a service and publishing the geo-tagged image
                        geo_image = ((event_image, image), (event, message))
                        break

                if geo_image is None:
                    print("Could not sync image and gps data")
                    continue

    async def run(self) -> None:
        # start the subscribe routines
        tasks: list[asyncio.Task] = []
        for subscription in self.subscriptions:
            tasks.append(asyncio.create_task(self._subscribe(subscription)))
        # wait for the subscribe routines to finish
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Example of subscribing to events.")
    parser.add_argument("--config", type=Path, required=True, help="The system config.")
    parser.add_argument("--time-delta", type=float, default=0.1, help="The time delta threshold.")
    args = parser.parse_args()

    # create a client to the camera service
    service_config: EventServiceConfigList = proto_from_json_file(args.config, EventServiceConfigList())

    # create the multi-client subscriber
    subscriber = GeoTaggedImageSubscriber(service_config, time_delta=args.time_delta)

    asyncio.run(subscriber.run())
