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

import logging
import time
from enum import IntEnum
from struct import pack
from struct import unpack

from farm_ng.canbus import amiga_v6_pb2
from farm_ng.canbus import canbus_pb2
from farm_ng.core.stamp import timestamp_from_monotonic
from farm_ng.core.timestamp_pb2 import Timestamp

# Important CAN node IDs
DASHBOARD_NODE_ID = 0xE
PENDANT_NODE_ID = 0xF
BRAIN_NODE_ID = 0x1F


class NodeState(IntEnum):
    """State of the node (farm-ng device)."""

    BOOTUP = 0x00  # Boot up / Initializing
    STOPPED = 0x04  # Stopped
    OPERATIONAL = 0x05  # Operational
    PRE_OPERATIONAL = 0x7F  # Pre-Operational


class PendantButtons(IntEnum):
    """Bit field for pendant buttons."""

    PAUSE = 0x01  # Square
    BRAKE = 0x02  # Circle
    PTO = 0x04  # Triangle
    CRUISE = 0x08  # Cross (X)
    LEFT = 0x10  # D-pad left
    UP = 0x20  # D-pad up
    RIGHT = 0x40  # D-pad right
    DOWN = 0x80  # D-pad down


class AmigaControlState(IntEnum):
    """State of the Amiga vehicle control unit (VCU)"""

    # TODO: add some comments about this states
    STATE_BOOT = 0
    STATE_MANUAL_READY = 1
    STATE_MANUAL_ACTIVE = 2
    STATE_CC_ACTIVE = 3
    STATE_AUTO_READY = 4
    STATE_AUTO_ACTIVE = 5
    STATE_ESTOPPED = 6


class ActuatorCommands(IntEnum):
    """Commands for the linear and rotary actuators."""

    passive = 0x0
    forward = 0x1
    stopped = 0x2
    reverse = 0x3


def actuator_bits_cmd(
    a0=ActuatorCommands.passive, a1=ActuatorCommands.passive, a2=ActuatorCommands.passive, a3=ActuatorCommands.passive
):
    """Returns the command bits for up to four linear or rotary actuators."""
    return a0.value + (a1.value << 2) + (a2.value << 4) + (a3.value << 6)


def actuator_bits_read(bits):
    """Parses the command bits for up to four linear or rotary actuators."""
    a0 = ActuatorCommands(bits & 0x3)
    a1 = ActuatorCommands((bits >> 2) & 0x3)
    a2 = ActuatorCommands((bits >> 4) & 0x3)
    a3 = ActuatorCommands((bits >> 6) & 0x3)
    return (a0, a1, a2, a3)


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


class FarmngHeartbeat(Packet):
    """Custom Heartbeat message = status sent regularly by farm-ng components."""

    format = "<BI3s"
    cob_id = 0x700

    def __init__(self, node_state: NodeState = NodeState.BOOTUP, ticks_ms: int = 0, serial_number=bytes()):
        self.node_state = node_state
        self.ticks_ms = ticks_ms
        self.serial_number = serial_number

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data."""
        return pack(self.format, self.node_state, self.ticks_ms, self.serial_number[:3])

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""
        (node_state, self.ticks_ms, self.serial_number) = unpack(self.format, data)
        self.node_state = NodeState(node_state)

    def __str__(self):
        return f"node_state: {self.node_state} ticks_ms: {self.ticks_ms} serial_number: {self.serial_number}"


def make_amiga_rpdo1_proto(
    state_req: AmigaControlState = AmigaControlState.STATE_ESTOPPED,
    cmd_speed: float = 0.0,
    cmd_ang_rate: float = 0.0,
    pto_bits: int = 0x0,
    hbridge_bits: int = 0x0,
) -> canbus_pb2.RawCanbusMessage:
    """Creates a canbus_pb2.RawCanbusMessage.

    Uses the AmigaRpdo1 structure and formatting, that can be sent
    directly to the canbus service to be formatted and send on the CAN bus.

    WARNING: Deprecated starting with farm-ng-amiga v2.3.0
    Please use AmigaRpdo1.to_raw_canbus_message() instead.

    Args:
        state_req: State of the Amiga vehicle control unit (VCU).
        cmd_speed: Command speed in meters per second.
        cmd_ang_rate: Command angular rate in radians per second.
        pto_bits: byte with encoded bits for PTO auto control
        hbridge_bits: byte with encoded bits for h-bridge auto control

    Returns:
        An instance of a canbus_pb2.RawCanbusMessage.
    """
    logging.warning("make_amiga_rpdo1_proto is deprecated as of v2.3.0")
    logging.warning("Use AmigaRpdo1.to_raw_canbus_message() instead.")

    # TODO: add some checkers, or make python CHECK_API
    return canbus_pb2.RawCanbusMessage(
        id=AmigaRpdo1.cob_id + DASHBOARD_NODE_ID,
        data=AmigaRpdo1(
            state_req=state_req,
            cmd_speed=cmd_speed,
            cmd_ang_rate=cmd_ang_rate,
            pto_bits=pto_bits,
            hbridge_bits=hbridge_bits,
        ).encode(),
    )


class AmigaRpdo1(Packet):
    """State, speed, and angular rate command (request) sent to the Amiga vehicle control unit (VCU).

    New in fw v0.1.9 / farm-ng-amiga v0.0.7: Add pto & hbridge control. Message data is now 8 bytes (was 5).
    """

    cob_id = 0x200

    def __init__(
        self,
        state_req: AmigaControlState = AmigaControlState.STATE_ESTOPPED,
        cmd_speed: float = 0.0,
        cmd_ang_rate: float = 0.0,
        pto_bits: int = 0x0,
        hbridge_bits: int = 0x0,
    ):
        self.format = "<BhhBBx"
        self.legacy_format = "<Bhh"

        self.state_req = state_req
        self.cmd_speed = cmd_speed
        self.cmd_ang_rate = cmd_ang_rate
        self.pto_bits = pto_bits
        self.hbridge_bits = hbridge_bits

        self.stamp_packet(time.monotonic())

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data."""
        return pack(
            self.format,
            self.state_req,
            int(self.cmd_speed * 1000.0),
            int(self.cmd_ang_rate * 1000.0),
            self.pto_bits,
            self.hbridge_bits,
        )

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""
        if len(data) == 5:
            logging.warning("Please update dashboard firmware to >= v0.1.9 to use updated AmigaRpdo1 packet format.")

            (self.state_req, cmd_speed, cmd_ang_rate) = unpack(self.legacy_format, data)
            self.cmd_speed = cmd_speed / 1000.0
            self.cmd_ang_rate = cmd_ang_rate / 1000.0
        else:
            (self.state_req, cmd_speed, cmd_ang_rate, self.pto_bits, self.hbridge_bits) = unpack(self.format, data)
            self.cmd_speed = cmd_speed / 1000.0
            self.cmd_ang_rate = cmd_ang_rate / 1000.0

    def __str__(self):
        return "AMIGA RPDO1 Request state {} Command speed {:0.3f} Command angular rate {:0.3f}".format(
            self.state_req, self.cmd_speed, self.cmd_ang_rate
        ) + " Command PTO bits 0x{:x} Command h-bridge bits 0x{:x}".format(self.pto_bits, self.hbridge_bits)

    def to_raw_canbus_message(self) -> canbus_pb2.RawCanbusMessage:
        """Packs the class data into a canbus_pb2.RawCanbusMessage.

        Returns: An instance of a canbus_pb2.RawCanbusMessage.
        """
        return canbus_pb2.RawCanbusMessage(
            stamp=self.stamp.stamp, id=self.cob_id + DASHBOARD_NODE_ID, data=self.encode()
        )


class AmigaTpdo1(Packet):
    """State, speed, and angular rate of the Amiga vehicle control unit (VCU).

    New in fw v0.1.9 / farm-ng-amiga v0.0.7: Add pto & hbridge control. Message data is now 8 bytes (was 5).

    New in fw v0.6.0 / farm-ng-amiga v2.4.0: Add SOC (state of charge) to the message.
    """

    cob_id = 0x180

    def __init__(
        self,
        state: AmigaControlState = AmigaControlState.STATE_ESTOPPED,
        meas_speed: float = 0.0,
        meas_ang_rate: float = 0.0,
        pto_bits: int = 0x0,
        hbridge_bits: int = 0x0,
        soc: int = 0x0,
    ):
        self.format = "<BhhBBB"
        self.legacy_format = "<Bhh"

        self.state = state
        self.meas_speed = meas_speed
        self.meas_ang_rate = meas_ang_rate
        self.pto_bits = pto_bits
        self.hbridge_bits = hbridge_bits
        self.soc = soc

        self.stamp_packet(time.monotonic())

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data."""
        return pack(
            self.format,
            self.state,
            int(self.meas_speed * 1000.0),
            int(self.meas_ang_rate * 1000.0),
            self.pto_bits,
            self.hbridge_bits,
            self.soc,
        )

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""
        if len(data) == 5:
            logging.warning("Please update dashboard firmware to >= v0.1.9 to use updated AmigaTpdo1 packet format.")

            (self.state, meas_speed, meas_ang_rate) = unpack(self.legacy_format, data)
            self.meas_speed = meas_speed / 1000.0
            self.meas_ang_rate = meas_ang_rate / 1000.0
        else:
            (self.state, meas_speed, meas_ang_rate, self.pto_bits, self.hbridge_bits, self.soc) = unpack(
                self.format, data
            )
            self.meas_speed = meas_speed / 1000.0
            self.meas_ang_rate = meas_ang_rate / 1000.0

    def to_proto(self) -> amiga_v6_pb2.AmigaTpdo1:
        """Packs the class data into an AmigaTpdo1 proto message.

        Returns: An instance of an AmigaTpdo1 proto.
        """
        return amiga_v6_pb2.AmigaTpdo1(
            node_id=DASHBOARD_NODE_ID,
            stamp=self.stamp.stamp,
            control_state=self.state,
            measured_speed=self.meas_speed,
            measured_angular_rate=self.meas_ang_rate,
            pto_bits=self.pto_bits,
            hbridge_bits=self.hbridge_bits,
            state_of_charge=self.soc,
        )

    @classmethod
    def from_proto(cls, proto: amiga_v6_pb2.AmigaTpdo1) -> AmigaTpdo1:
        """Creates an instance of the class from a proto message.

        Args:
            proto: The AmigaTpdo1 proto message to parse.
        """
        # Check for correct proto
        if not isinstance(proto, amiga_v6_pb2.AmigaTpdo1):
            raise TypeError(f"Expected amiga_v6_pb2.AmigaTpdo1 proto, received {type(proto)}")

        obj = cls()  # Does not call __init__
        obj.stamp_packet(proto.stamp)
        obj.state = AmigaControlState(proto.control_state)
        obj.meas_speed = proto.measured_speed
        obj.meas_ang_rate = proto.measured_angular_rate
        obj.pto_bits = proto.pto_bits
        obj.hbridge_bits = proto.hbridge_bits
        obj.soc = proto.state_of_charge
        return obj

    @classmethod
    def from_raw_canbus_message(cls, message: canbus_pb2.RawCanbusMessage) -> AmigaTpdo1:
        """Parses a canbus_pb2.RawCanbusMessage.

        IFF the message came from the dashboard and contains AmigaTpdo1 structure,
        formatting, and cobid.

        Args:
            message: The raw canbus message to parse.

        Returns:
            The parsed AmigaTpdo1 message.
        """
        if message.id != cls.cob_id + DASHBOARD_NODE_ID:
            raise ValueError(f"Expected message from dashboard, received message from node {message.id - cls.cob_id}")

        return cls.from_can_data(message.data, stamp=message.stamp)

    def __str__(self):
        return "AMIGA TPDO1 Amiga state {} Measured speed {:0.3f} Measured angular rate {:0.3f} @ time {}".format(
            self.state, self.meas_speed, self.meas_ang_rate, self.stamp.stamp
        ) + " PTO bits 0x{:x} h-bridge bits 0x{:x} charge level: {}%".format(self.pto_bits, self.hbridge_bits, self.soc)


def parse_amiga_tpdo1_proto(message: canbus_pb2.RawCanbusMessage) -> AmigaTpdo1 | None:
    """Parses a canbus_pb2.RawCanbusMessage.

    IFF the message came from the dashboard and contains AmigaTpdo1 structure,
    formatting, and cobid.

    WARNING: Deprecated starting with farm-ng-amiga v2.3.0
    Please use AmigaTpdo1.from_raw_canbus_message() instead.

    Args:
        message: The raw canbus message to parse.

    Returns:
        The parsed AmigaTpdo1 message, or None if the message is not a valid AmigaTpdo1 message.
    """
    logging.warning("parse_amiga_tpdo1_proto is deprecated as of v2.3.0")
    logging.warning("Use AmigaTpdo1.from_raw_canbus_message() instead.")

    # TODO: add some checkers, or make python CHECK_API
    if message.id != AmigaTpdo1.cob_id + DASHBOARD_NODE_ID:
        return None
    return AmigaTpdo1.from_can_data(message.data, stamp=message.stamp)


class MotorControllerStatus(IntEnum):
    """Values representing the status of the motor controller."""

    PRE_OPERATIONAL = 0  # the motor is not ready to run
    IDLE = 1  # the motor is waiting to start
    POST_OPERATIONAL = 2  # the motor already started
    # NOTE: the motor controller does not have a "running" state
    RUN = 3  # the motor is running
    FAULT = 4  # the motor controller is in fault mode


class MotorState:
    """Values representing the state of the motor.

    Amalgamates values from multiple CAN packets.
    """

    def __init__(
        self,
        id: int = 0,
        status: MotorControllerStatus = MotorControllerStatus.FAULT,
        rpm: int = 0,
        voltage: float = 0.0,
        current: float = 0.0,
        temperature: int = 0,
        timestamp: float = time.monotonic(),
    ):
        self.id: int = id
        self.status: MotorControllerStatus = status
        self.rpm: int = rpm
        self.voltage: float = voltage
        self.current: float = current
        self.temperature: int = temperature
        self.timestamp: float = timestamp

    def to_proto(self) -> canbus_pb2.MotorState:
        """Returns the data contained by the class encoded as CAN message data."""
        proto = canbus_pb2.MotorState(
            id=self.id,
            status=self.status.value,
            rpm=self.rpm,
            voltage=self.voltage,
            current=self.current,
            temperature=self.temperature,
            stamp=self.timestamp,
        )
        return proto

    @classmethod
    def from_proto(cls, proto: canbus_pb2.MotorState):
        obj = cls()  # Does not call __init__
        obj.id = proto.id
        obj.status = MotorControllerStatus(proto.status)
        obj.rpm = proto.rpm
        obj.voltage = proto.voltage
        obj.current = proto.current
        obj.temperature = proto.temperature
        obj.timestamp = proto.stamp
        return obj

    def __str__(self):
        return (
            "Motor state - id {:01X} status {} rpm {:4} voltage {:.3f} "
            "current {:.3f} temperature {:.1f} @ time {:.3f}".format(
                self.id, self.status.name, self.rpm, self.voltage, self.current, self.temperature, self.timestamp
            )
        )


class PendantState(Packet):
    """State of the Pendant (joystick position & pressed buttons)"""

    scale = 32767
    format = "<hhI"
    cob_id = 0x180

    def __init__(self, x=0, y=0, buttons=0):
        self.x = x  # [-1.0, 1.0] => [left, right]
        self.y = y  # [-1.0, 1.0] => [reverse, forward]
        self.buttons = buttons
        self.stamp_packet(time.monotonic())

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data."""
        return pack(self.format, int(self.x * self.scale), int(self.y * self.scale), self.buttons)

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""

        (xi, yi, self.buttons) = unpack(self.format, data)
        self.x = xi / self.scale
        self.y = yi / self.scale

    def to_proto(self) -> amiga_v6_pb2.PendantState:
        """Packs the class data into a PendantState proto message.

        Returns: An instance of a PendantState proto.
        """
        return amiga_v6_pb2.PendantState(
            node_id=PENDANT_NODE_ID, stamp=self.stamp.stamp, x=self.x, y=self.y, buttons=self.buttons
        )

    @classmethod
    def from_proto(cls, proto: amiga_v6_pb2.PendantState) -> PendantState:
        """Creates an instance of the class from a proto message.

        Args:
            proto: The PendantState proto message to parse.
        """
        # Check for correct proto
        if not isinstance(proto, amiga_v6_pb2.PendantState):
            raise TypeError(f"Expected amiga_v6_pb2.PendantState proto, received {type(proto)}")

        obj = cls()
        obj.stamp_packet(proto.stamp)
        obj.x = proto.x
        obj.y = proto.y
        obj.buttons = proto.buttons
        return obj

    @classmethod
    def from_raw_canbus_message(cls, message: canbus_pb2.RawCanbusMessage) -> PendantState:
        """Parses a canbus_pb2.RawCanbusMessage.

        IFF the message came from the pendant and contains PendantState structure,
        formatting, and cobid.

        Args:
            message: The raw canbus message to parse.

        Returns:
            The parsed PendantState message.
        """
        if message.id != cls.cob_id + PENDANT_NODE_ID:
            raise ValueError(f"Expected message from pendant, received message from node {message.id}")

        return cls.from_can_data(message.data, stamp=message.stamp)

    def is_button_pressed(self, button: PendantButtons) -> bool:
        """Returns True if the button is pressed."""
        if not isinstance(button, PendantButtons):
            raise TypeError(f"Expected PendantButtons, received {type(button)}")
        return bool(self.buttons & button)

    def __str__(self):
        return "x {:0.3f} y {:0.3f} buttons {}".format(self.x, self.y, self.buttons)


class BugDispenserCommand(Packet):
    """Bug dispenser rate in m/drop (request) sent to the Amiga dashboard."""

    cob_id = 0x400
    format = "<3B5x"
    scale = 10.0

    def __init__(self, rate0=0, rate1=0, rate2=0):
        self.rate0 = rate0
        self.rate1 = rate1
        self.rate2 = rate2
        self.stamp_packet(time.monotonic())

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data."""

        if any(rate > 25.5 or rate < 0.0 for rate in [self.rate0, self.rate1, self.rate2]):
            raise ValueError("Rates must be between 0.0 and 25.5 mL/m")

        return pack(
            self.format, int(self.rate0 * self.scale), int(self.rate1 * self.scale), int(self.rate2 * self.scale)
        )

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""
        rate0, rate1, rate2 = unpack(self.format, data)

        # Convert rates to m/drop
        self.rate0 = rate0 / self.scale
        self.rate1 = rate1 / self.scale
        self.rate2 = rate2 / self.scale

    def __str__(self):
        """Returns a string representation of the class."""
        return f"BugDispenserCommand: Rates: {self.rate0}, {self.rate1}, {self.rate2}"

    def to_raw_canbus_message(self) -> canbus_pb2.RawCanbusMessage:
        """Packs the class data into a canbus_pb2.RawCanbusMessage."""
        return canbus_pb2.RawCanbusMessage(
            stamp=self.stamp.stamp, id=self.cob_id + DASHBOARD_NODE_ID, data=self.encode()
        )


class BugDispenserState(Packet):
    """Bug dispenser rate in mL/m, 8-bit counter (response) received from the Amiga dashboard."""

    cob_id = 0x380
    format = "<6B2x"
    scale = 10.0

    def __init__(self, rate0=0, counter0=0, rate1=0, counter1=0, rate2=0, counter2=0):
        self.rate0 = rate0
        self.rate1 = rate1
        self.rate2 = rate2
        self.counter0 = counter0
        self.counter1 = counter1
        self.counter2 = counter2
        self.stamp_packet(time.monotonic())

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data.

        Data is encoded as follows:
        R1 C1 R2 C2 R3 C3
        """

        if any(rate > 25.5 or rate < 0.0 for rate in [self.rate0, self.rate1, self.rate2]):
            raise ValueError("Rates must be between 0 and 25.5 mL/m")

        if any(counter > 255 or counter < 0 for counter in [self.counter0, self.counter1, self.counter2]):
            raise ValueError("Counters must be between 0 and 255")

        return pack(
            self.format,
            int(self.rate0 * self.scale),
            self.counter0,
            int(self.rate1 * self.scale),
            self.counter1,
            int(self.rate2 * self.scale),
            self.counter2,
        )

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""

        rate0, counter0, rate1, counter1, rate2, counter2 = unpack(self.format, data)

        # Convert rates to m/drop
        self.rate0 = rate0 / self.scale
        self.rate1 = rate1 / self.scale
        self.rate2 = rate2 / self.scale

        self.counter0 = counter0
        self.counter1 = counter1
        self.counter2 = counter2

    @classmethod
    def from_raw_canbus_message(cls, message: canbus_pb2.RawCanbusMessage) -> BugDispenserState:
        """Parses a canbus_pb2.RawCanbusMessage."""
        return cls.from_can_data(message.data, message.stamp)

    def __str__(self):
        """Returns a string representation of the class."""
        return (
            f"BugDispenserState: Rates: {self.rate0}, {self.rate1}, {self.rate2} "
            f"| Counters: {self.counter0}, {self.counter1}, {self.counter2}"
        )
