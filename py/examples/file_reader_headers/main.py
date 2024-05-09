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


def main(file_name: str, skip_calibrations: bool) -> None:
    # create the file reader
    reader = EventsFileReader(file_name)
    success: bool = reader.open()
    if not success:
        raise RuntimeError(f"Failed to open events file: {file_name}")

    # get the index of the events file
    events_index: list[EventLogPosition] = reader.get_index()

    # structure the index as a dictionary of lists of events
    events_dict: dict[str, list[EventLogPosition]] = build_events_dict(events_index)

    # print number of events in each topic, sorted by count
    print("Number of events in each topic:")
    for key in sorted(events_dict.keys(), key=lambda k: len(events_dict[k])):
        print(f"{key}: {len(events_dict[key])}")
    print("\n#############################################\n")

    header_events = []
    for key in events_dict.keys():
        if "header" in key:
            if skip_calibrations and "calibration" in key:
                continue
            header_events.extend(events_dict[key])

    print("Header events:")
    for event_log in header_events:
        # parse the message
        print(f"### {event_log.event.uri.path} ###")
        print(event_log.read_message())

    assert reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python main.py", description="Event file reader example for parsing header messages."
    )
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file.")
    parser.add_argument("--skip-calibrations", action="store_true", help="Skip camera calibration header messages.")
    args = parser.parse_args()
    main(args.file_name, args.skip_calibrations)
