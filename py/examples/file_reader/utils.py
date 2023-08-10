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
"""Utility functions for working with events."""
from __future__ import annotations

from collections import defaultdict

from farm_ng.core.events_file_reader import EventLogPosition


def build_events_dict(events_index: list[EventLogPosition]) -> dict[str, list[EventLogPosition]]:
    """Build a dictionary of lists of events, where the key is the path of the event.

    Args:
        events_index (list[EventLogPosition]): [description]

    Returns:
        dict[str, list[EventLogPosition]]: [description]
    """
    events_dict: dict[str, list[EventLogPosition]] = defaultdict(list)
    for event_index in events_index:
        # NOTE: this is how we get the service name from the event uri
        # TODO: this should be done by the event service
        service_name = event_index.event.uri.query.split("&")[-1].split("=")[-1]
        topic_name = f"/{service_name}{event_index.event.uri.path}"
        events_dict[topic_name].append(event_index)
    return events_dict
