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

import time
from enum import IntEnum
from struct import pack
from struct import unpack

from farm_ng.canbus import amiga_v6_pb2
from farm_ng.canbus import canbus_pb2
from farm_ng.core.stamp import timestamp_from_monotonic
from farm_ng.core.timestamp_pb2 import Timestamp

# TODO: add some comments about the CAN bus protocol
DASHBOARD_NODE_ID = 0xE
PENDANT_NODE_ID = 0xF
BRAIN_NODE_ID = 0x1F
SDK_NODE_ID = 0x2A


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
    passive = 0x0
    forward = 0x1
    stopped = 0x2
    reverse = 0x3


def actuator_bits_cmd(
    a0=ActuatorCommands.passive, a1=ActuatorCommands.passive, a2=ActuatorCommands.passive, a3=ActuatorCommands.passive
):
    return a0.value + (a1.value << 2) + (a2.value << 4) + (a3.value << 6)


def actuator_bits_read(bits):
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


def make_amiga_rpdo1_proto(
    state_req: AmigaControlState, cmd_speed: float, cmd_ang_rate: float, pto_bits: int = 0x0, hbridge_bits: int = 0x0
) -> canbus_pb2.RawCanbusMessage:
    """Creates a canbus_pb2.RawCanbusMessage.

    Uses the AmigaRpdo1 structure and formatting, that can be sent
    directly to the canbus service to be formatted and send on the CAN bus.

    Args:
        state_req: State of the Amiga vehicle control unit (VCU).
        cmd_speed: Command speed in meters per second.
        cmd_ang_rate: Command angular rate in radians per second.

    Returns:
        An instance of a canbus_pb2.RawCanbusMessage.
    """
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
            # TODO: Instate warning when dashboard fw v0.1.9 is released
            # warnings.warn(
            #     "Please update dashboard firmware to >= v0.1.9."
            #     " New AmigaTpdo1 packets include more data. Support will be removed in farm_ng_amiga v0.0.9",
            #     stacklevel=2,
            # )
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


class AmigaTpdo1(Packet):
    """State, speed, and angular rate of the Amiga vehicle control unit (VCU).

    New in fw v0.1.9 / farm-ng-amiga v0.0.7: Add pto & hbridge control. Message data is now 8 bytes (was 5).
    """

    cob_id = 0x180

    def __init__(
        self,
        state: AmigaControlState = AmigaControlState.STATE_ESTOPPED,
        meas_speed: float = 0.0,
        meas_ang_rate: float = 0.0,
        pto_bits: int = 0x0,
        hbridge_bits: int = 0x0,
    ):
        self.format = "<BhhBBx"
        self.legacy_format = "<Bhh"

        self.state = state
        self.meas_speed = meas_speed
        self.meas_ang_rate = meas_ang_rate
        self.pto_bits = pto_bits
        self.hbridge_bits = hbridge_bits

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
        )

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""
        if len(data) == 5:
            # TODO: Instate warning when dashboard fw v0.1.9 is released
            # warnings.warn(
            #     "Please update dashboard firmware to >= v0.1.9."
            #     " New AmigaTpdo1 packets include more data. Support will be removed in farm_ng_amiga v0.0.9",
            #     stacklevel=2,
            # )
            (self.state, meas_speed, meas_ang_rate) = unpack(self.legacy_format, data)
            self.meas_speed = meas_speed / 1000.0
            self.meas_ang_rate = meas_ang_rate / 1000.0
        else:
            (self.state, meas_speed, meas_ang_rate, self.pto_bits, self.hbridge_bits) = unpack(self.format, data)
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
        return obj

    def __str__(self):
        return "AMIGA TPDO1 Amiga state {} Measured speed {:0.3f} Measured angular rate {:0.3f} @ time {}".format(
            self.state, self.meas_speed, self.meas_ang_rate, self.stamp.stamp
        ) + " PTO bits 0x{:x} h-bridge bits 0x{:x}".format(self.pto_bits, self.hbridge_bits)


def parse_amiga_tpdo1_proto(message: canbus_pb2.RawCanbusMessage) -> AmigaTpdo1 | None:
    """Parses a canbus_pb2.RawCanbusMessage.

    IFF the message came from the dashboard and contains AmigaTpdo1 structure,
    formatting, and cobid.

    Args:
        message: The raw canbus message to parse.

    Returns:
        The parsed AmigaTpdo1 message, or None if the message is not a valid AmigaTpdo1 message.
    """
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
