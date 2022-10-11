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
        def _make_frame(i):
            frame = oak_pb2.OakFrame()
            frame.image_data = bytes(i * [1, 2, 3, 4, 5, 6, 7, 8, 9])
            return frame

        frames = [_make_frame(i + 1) for i in range(4)]
        with EventsFileWriter(log_file) as writer:
            writer.write(path="oak0/frame", message=frames[0])
            writer.write(path="oak1/frame", message=frames[1])
            writer.write(path="oak0/frame", message=frames[2])
            writer.write(path="oak0/frame", message=frames[3])

        # check time based
        with EventsFileReader(log_file) as reader:
            messages_stream = reader.read_messages()
            for i, (event, msg) in enumerate(messages_stream):
                assert msg.image_data == frames[i].image_data
                assert any(x in event.uri.path for x in ["oak0", "oak1"])

        # check frame based
        with EventsFileReader(log_file) as reader:
            oak0, oak1 = reader.uris()
            assert reader.num_events(oak0) == 3
            assert reader.num_events(oak1) == 1
            # frame 1
            event, offset = reader.get_event(oak0, 0)
            msg = reader.read_message(event, offset)
            assert msg.image_data == frames[0].image_data
            # frame 2
            event, offset = reader.get_event(oak0, 1)
            msg = reader.read_message(event, offset)
            assert msg.image_data == frames[2].image_data
            # frame 3
            event, offset = reader.get_event(oak0, 2)
            msg = reader.read_message(event, offset)
            assert msg.image_data == frames[3].image_data
