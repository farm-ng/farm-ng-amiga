from __future__ import annotations
from struct import pack, unpack
import time
from farm_ng.core.stamp import timestamp_from_monotonic
from farm_ng.core.timestamp_pb2 import Timestamp
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus import tool_control_pb2

# Important CAN node IDs
DASHBOARD_NODE_ID = 0xE

class Packet:
    """Base class inherited by all CAN message data structures."""

    @classmethod
    def from_can_data(cls, data, stamp: float):
        """Unpack CAN data directly into CAN message data structure."""
        obj = cls()  # Does not call __init__
        obj.decode(data)
        obj.stamp_packet(stamp)
        return obj

    def stamp_packet(self, stamp: float):
        """Time most recent message was received."""
        self.stamp: Timestamp = timestamp_from_monotonic("canbus/packet", stamp)

    def fresh(self, thresh_s: float = 0.5):
        """Returns False if the most recent message is older than ``thresh_s`` in seconds."""
        return self.age() < thresh_s

    def age(self):
        """Age of the most recent message."""
        return time.monotonic() - self.stamp.stamp

class BugDispenserRpdo3(Packet):
    """Bug dispenser rate in m/drop (request) sent to the Amiga dashboard."""

    cob_id = 0x400

    def __init__(self, rate1=0, rate2=0, rate3=0):
        self.rate1 = rate1
        self.rate2 = rate2
        self.rate3 = rate3
        self.format = '<3B5x'  # 3 bytes for rates, 5 bytes padding
        self.stamp_packet(time.monotonic())

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data."""

        if any(rate > 25.5 or rate < 0.0 for rate in [self.rate1, self.rate2, self.rate3]):
            raise ValueError("Rates must be between 0.0 and 25.5 m/drop")

        return pack(self.format, int(self.rate1 * 10.0), int(self.rate2 * 10.0), int(self.rate3 * 10.0))

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""

        self.rate1, self.rate2, self.rate3 = unpack(self.format, data)
        self.rate1 /= 10.0
        self.rate2 /= 10.0
        self.rate3 /= 10.0

    def __str__(self):
        """Returns a string representation of the class."""
        return f"BugDispenserRpdo1: Rates: {self.rate1}, {self.rate2}, {self.rate3}"

    def to_raw_canbus_message(self) -> canbus_pb2.RawCanbusMessage:
        """Packs the class data into a canbus_pb2.RawCanbusMessage."""
        return canbus_pb2.RawCanbusMessage(
            stamp=self.stamp.stamp, id=self.cob_id + DASHBOARD_NODE_ID, data=self.encode()
        )


class BugDispenserTpdo3(Packet):
    """Bug dispenser rate in m/drop, 8-bit counter (response) received from the Amiga dashboard."""

    cob_id = 0x380

    def __init__(self, rate1=0, counter1=0, rate2=0, counter2=0, rate3=0, counter3=0):
        self.rate1 = rate1 & 0xFF
        self.counter1 = counter1 & 0xFF
        self.rate2 = rate2 & 0xFF
        self.counter2 = counter2 & 0xFF
        self.rate3 = rate3 & 0xFF
        self.counter3 = counter3 & 0xFF
        self.format = '<6B2x'  # 3 bytes for rates, 3 bytes for counters, 2 padding bytes
        self.stamp_packet(time.monotonic())

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data.

        Data is encoded as follows:
        R1 C1 R2 C2 R3 C3
        """

        if any(rate > 25.5 or rate < 0.0 for rate in [self.rate1, self.rate2, self.rate3]):
            raise ValueError("Rates must be between 0 and 25.5 m/drop")

        if any(counter > 255 or counter < 0 for counter in [self.counter1, self.counter2, self.counter3]):
            raise ValueError("Counters must be between 0 and 255")

        return pack(
            self.format,
            int(self.rate1 * 10.0),
            self.counter1,
            int(self.rate2 * 10.0),
            self.counter2,
            int(self.rate3 * 10.0),
            self.counter3,
        )

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""
        self.rate1, self.counter1, self.rate2, self.counter2, self.rate3, self.counter3 = unpack(self.format, data)

        self.rate1 /= 10.0
        self.rate2 /= 10.0
        self.rate3 /= 10.0

    def to_raw_canbus_message(self) -> canbus_pb2.RawCanbusMessage:
        """Packs the class data into a canbus_pb2.RawCanbusMessage."""
        return canbus_pb2.RawCanbusMessage(
            stamp=self.stamp.stamp, id=self.cob_id + DASHBOARD_NODE_ID, data=self.encode()
        )

    def to_proto(self) -> tool_control_pb2.BugDispenserTpdo3:
        """Packs the class data into a BugDispenserTpdo1 proto message."""
        return tool_control_pb2.BugDispenserTpdo3(
            bug_dispenser_1_rate=self.rate1,
            bug_dispenser_1_counter=self.counter1,
            bug_dispenser_2_rate=self.rate2,
            bug_dispenser_2_counter=self.counter2,
            bug_dispenser_3_rate=self.rate3,
            bug_dispenser_3_counter=self.counter3,
        )

    @classmethod
    def from_proto(cls, proto: tool_control_pb2.BugDispenserTpdo3) -> BugDispenserTpdo3:
        """Creates an instance of the class from a proto message."""
        if not isinstance(proto, tool_control_pb2.BugDispenserTpdo3):
            raise TypeError(f"Expected tool_control_pb2.BugDispenserTpdo1 proto, received {type(proto)}")
        obj = cls()
        obj.rate1 = proto.bug_dispenser_1_rate
        obj.counter1 = proto.bug_dispenser_1_counter
        obj.rate2 = proto.bug_dispenser_2_rate
        obj.counter2 = proto.bug_dispenser_2_counter
        obj.rate3 = proto.bug_dispenser_3_rate
        obj.counter3 = proto.bug_dispenser_3_counter
        obj.stamp_packet(proto.stamp)
        return obj

    @classmethod
    def from_raw_canbus_message(cls, message: canbus_pb2.RawCanbusMessage) -> BugDispenserTpdo3:
        """Parses a canbus_pb2.RawCanbusMessage."""
        return cls.from_can_data(message.data, message.stamp)

    def __str__(self):
        """Returns a string representation of the class."""
        return (
            f"BugDispenserTpdo1: Rates: {self.rate1}, {self.rate2}, {self.rate3} "
            f"| Counters: {self.counter1}, {self.counter2}, {self.counter3}"
        )





# Rpdo1 example
message = BugDispenserRpdo3(rate1=10.58, rate2=18.3462, rate3=0.559)
encoded_message = message.encode()
print(f"Encoded CAN message: {encoded_message.hex()}")
print(f"Len in bytes: {len(encoded_message)}")

decoded_message = BugDispenserRpdo3()
decoded_message.decode(encoded_message)
print(decoded_message)

# To RawCanbusMessage
raw_message = message.to_raw_canbus_message()
print(raw_message)

print("-" * 80)

# Tpdo1 example
message = BugDispenserTpdo3(rate1=1, counter1=138, rate2=15, counter2=200, rate3=12, counter3=255)
encoded_message = message.encode()
print(f"Encoded CAN message: {encoded_message.hex()}")
print(f"Len in bytes: {len(encoded_message)}")

decoded_message = BugDispenserTpdo3()
decoded_message.decode(encoded_message)
print(decoded_message)

# To RawCanbusMessage   
raw_message = message.to_raw_canbus_message()
print(raw_message)

# To Proto
proto_message = message.to_proto()
print(proto_message)

# From Proto
message = BugDispenserTpdo3.from_proto(proto_message)
print(message)

print("-" * 80)

# Error
try:
    message = BugDispenserRpdo3(rate1=30.0).encode()
except ValueError as e:
    print(e)

try:
    message = BugDispenserTpdo3(rate1=300).encode()
except ValueError as e:
    print(e)
