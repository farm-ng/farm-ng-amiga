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
from pathlib import Path

import pytest
from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.core.events_file_writer import EventsFileWriter
from farm_ng.oak import oak_pb2


@pytest.fixture(name="log_base")
def fixture_log_file(tmpdir) -> Path:
    return Path(tmpdir) / "event"


@pytest.fixture(name="reader_log_file")
def fixture_reader_log_file(tmpdir) -> Path:
    return Path(tmpdir) / "event.0000.bin"


class TestEventsWriter:
    def test_smoke(self, log_base: Path) -> None:
        with EventsFileWriter(log_base) as writer:
            assert writer.is_open()

    def test_write(self, log_base: Path) -> None:
        with EventsFileWriter(log_base) as writer:
            frame = oak_pb2.OakFrame()
            frame.image_data = bytes([1, 2, 3, 4, 5, 6, 7, 8, 9])
            writer.write(path="oak/frame", message=frame)


class TestEventsReader:
    def test_smoke(self, log_base: Path, reader_log_file: Path) -> None:
        # touch file
        with EventsFileWriter(log_base) as _:
            pass
        with EventsFileReader(reader_log_file) as reader:
            assert reader.is_open()

    def test_write_read(self, log_base: Path, reader_log_file: Path) -> None:
        def _make_frame(i):
            frame = oak_pb2.OakFrame()
            frame.image_data = bytes(i * [1, 2, 3, 4, 5, 6, 7, 8, 9])
            return frame

        frames = [_make_frame(i + 1) for i in range(4)]
        with EventsFileWriter(log_base) as writer:
            writer.write(path="oak0/frame", message=frames[0])
            writer.write(path="oak1/frame", message=frames[1])
            writer.write(path="oak0/frame", message=frames[2])
            writer.write(path="oak0/frame", message=frames[3])

        # check time based
        with EventsFileReader(reader_log_file) as reader:
            messages_stream = reader.read_messages()
            for i, (event, msg) in enumerate(messages_stream):
                assert msg.image_data == frames[i].image_data
                assert any(x in event.uri.path for x in ["oak0", "oak1"])

        # check frame based
        with EventsFileReader(reader_log_file) as reader:
            events = reader.get_index()
            oak0, oak1 = sorted([*{x.event.uri.path for x in events}])
            oak0_events = [x for x in events if x.event.uri.path == oak0]
            oak1_events = [x for x in events if x.event.uri.path == oak1]
            assert len(oak0_events) == 3
            assert len(oak1_events) == 1

            # frame 1
            msg = oak0_events[0].read_message()
            assert msg.image_data == frames[0].image_data
            # frame 2
            msg = oak0_events[1].read_message()
            assert msg.image_data == frames[2].image_data
            # frame 3
            msg = oak0_events[2].read_message()
            assert msg.image_data == frames[3].image_data
