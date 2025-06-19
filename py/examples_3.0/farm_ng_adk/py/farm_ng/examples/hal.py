import pynng
from dataclasses import dataclass
import struct
from farm_ng.hal import imu_pb2 as hal_pb

@dataclass
class Duration:
    secs: int
    nanos: int

@dataclass
class Stamp:
    acqtime: Duration
    pubtime: Duration

@dataclass
class NngPubSubHeader:
    seq: int
    stamp: Stamp
    payload_checksum: int

def decode(buf: bytes) -> (str, NngPubSubHeader):
    try:
        nul_index = buf.index(0)
    except ValueError:
        raise ValueError("No null terminator found in prefix")

    prefix_buf = buf[:nul_index]
    prefix = prefix_buf.decode("utf-8", errors="strict")

    # Remaining payload after null terminator
    header_buf = buf[nul_index + 1:]
    if len(header_buf) < 44:
        raise ValueError("Payload too short to decode NngPubSubHeader")

    # Unpack layout: u64, u64, (u64, u32), (u64, u32), u32
    unpacked = struct.unpack('< Q Q QI QI I', header_buf[:44])
    if unpacked[0] != 10435029236456460496:
        raise ValueError("Invalid magic")

    header = NngPubSubHeader(
        seq=unpacked[1],
        stamp=Stamp(
            acqtime=Duration(secs=unpacked[2], nanos=unpacked[3]),
            pubtime=Duration(secs=unpacked[4], nanos=unpacked[5])),
        payload_checksum=unpacked[6]
    )

    payload = header_buf[44:]

    return (prefix, header, payload)

ADDRESS = "ipc:///tmp/farm_ng-amiga-hal"

def main():
    with pynng.Sub0() as sub:
        sub.subscribe(b'')
        sub.dial(ADDRESS)
        print(f"Listening for messages on {ADDRESS}...")
        while True:
            buf = sub.recv()

            (prefix, header, payload) = decode(buf)
            print(f"({prefix}): {header}, payload: {len(payload)} bytes")

            if prefix == "imu":
                imu = hal_pb.Imu()
                imu.ParseFromString(payload)
                print(f"{imu}")

if __name__ == "__main__":
    main()
