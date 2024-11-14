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

from farm_ng.core.events_file_reader import build_events_dict
from farm_ng.core.events_file_reader import EventLogPosition
from farm_ng.core.events_file_reader import EventsFileReader


def main(file_name: str) -> None:
    # create the file reader
    reader = EventsFileReader(file_name)
    success: bool = reader.open()
    if not success:
        raise RuntimeError(f"Failed to open events file: {file_name}")

    # get the index of the events file
    events_index: list[EventLogPosition] = reader.get_index()

    # structure the index as a dictionary of lists of events
    events_dict: dict[str, list[EventLogPosition]] = build_events_dict(events_index)
    print(f"All available topics: {sorted(events_dict.keys())}")

    can_events = events_dict["/data_collection/annotation"]
    print(f"Found {len(can_events)} annotated packets")

    for event_log in can_events:
        # parse the message
        sample = event_log.read_message()
        print(sample)

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python main.py", description="Event file reader example for parsing CAN messages."
    )
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    args = parser.parse_args()
    main(args.file_name)
