from pathlib import Path

import pytest

from farm_ng.core.events_file_reader import EventsFileReader
from farm_ng.core.events_file_writer import EventsFileWriter
from farm_ng.oak import oak_pb2


@pytest.fixture(name="log_file")
def fixture_log_file(tmpdir) -> Path:
    return Path(tmpdir) / "event.log"


class TestEventsWriter:
    def test_smoke(self, log_file: Path) -> None:
        with EventsFileWriter(log_file) as writer:
            assert writer.is_open()

    def test_write(self, log_file: Path) -> None:
        with EventsFileWriter(log_file) as writer:
            frame = oak_pb2.OakFrame()
            frame.image_data = bytes([1, 2, 3, 4, 5, 6, 7, 8, 9])
            writer.write(path="oak/frame", message=frame)


class TestEventsReader:
    def test_smoke(self, log_file: Path) -> None:
        # touch file
        with EventsFileWriter(log_file) as _:
            pass
        with EventsFileReader(log_file) as reader:
            assert reader.is_open()

    def test_write_read(self, log_file: Path) -> None:
        frame = oak_pb2.OakFrame()
        frame.image_data = bytes([1, 2, 3, 4, 5, 6, 7, 8, 9])
        with EventsFileWriter(log_file) as writer:
            writer.write(path="oak/frame", message=frame)

        with EventsFileReader(log_file) as reader:
            messages_stream = reader.read_messages()
            for event, msg in messages_stream:
                assert msg.image_data == frame.image_data
