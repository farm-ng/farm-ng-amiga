"""Example of splitting an events file into multiple smaller files."""
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
from pathlib import Path

from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.core.events_file_writer import EventsFileWriter


def main(file_name: Path, output_dir: Path, split_mb: int) -> None:
    """Splits a large events file into multiple smaller files.

    Args:
        file_name (Path): The path to the events file to split.
        output_dir (Path): The directory to write the split files to.
        split_mb (int): The size of each split file in MB.
    """
    # create the file reader
    reader = EventsFileReader(file_name)
    if not reader.open():
        raise RuntimeError(f"Failed to open events file: {file_name}")

    print(f"Opened events file: {file_name}")
    print(f"File length: {int(reader.file_length / 1e6)} MB")

    # Create the output directory to write the split files to
    if not output_dir.is_dir():
        raise RuntimeError(f"Invalid output directory: {output_dir}")

    file_root = file_name.stem.split(".")[0]
    split_dir: Path = output_dir / f"split_{file_root}"
    if split_dir.exists():
        raise RuntimeError(f"Directory already exists: {split_dir}. Not overwriting existing files.")

    split_dir.mkdir(parents=False, exist_ok=False)

    # Create the file writer
    writer = EventsFileWriter(split_dir / file_root, max_file_mb=split_mb)
    if not writer.open():
        raise RuntimeError(f"Failed to open events file: {writer}")

    print(f"Writing to {writer.file_name}")

    # Iterate over the events in the file and write them to the split files
    for event, message in reader.read_messages():
        writer.write(path=event.uri.path, message=message, timestamps=event.timestamps, write_stamps=False)

    # Close the reader and writer
    assert reader.close()
    assert writer.close()


if __name__ == "__main__":
    # Get the current directory
    cwd = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(prog="python main.py", description="Example to show how to split a log file.")
    parser.add_argument("--file-name", type=str, required=True, help="Path to the `events.bin` file to split.")
    parser.add_argument("--split-mb", type=int, required=True, help="Size of each split file in MB.")
    parser.add_argument(
        "--output-dir", type=str, default=str(cwd), help=f"Directory to write the split files to. Default is {cwd}"
    )
    args = parser.parse_args()
    main(Path(args.file_name), Path(args.output_dir), args.split_mb)
