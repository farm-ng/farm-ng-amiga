# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
# Copyright (c) farm-ng, inc. All rights reserved.
import time
from enum import IntEnum
from struct import pack
from struct import unpack
from typing import Optional

from farm_ng.canbus import canbus_pb2
from farm_ng.core.stamp import get_monotonic_now
from farm_ng.core.timestamp_pb2 import Timestamp

DASHBOARD_NODE_ID = 0xE
PENDANT_NODE_ID = 0xF
BRAIN_NODE_ID = 0x1F
SDK_NODE_ID = 0x2A


class AmigaControlState(IntEnum):
    """State of the Amiga vehicle control unit (VCU)"""

    STATE_BOOT = 0
    STATE_MANUAL_READY = 1
    STATE_MANUAL_ACTIVE = 2
    STATE_CC_ACTIVE = 3
    STATE_AUTO_READY = 4
    STATE_AUTO_ACTIVE = 5
    STATE_ESTOPPED = 6


class Packet:
    """Base class inherited by all CAN message data structures."""

    @classmethod
    def from_can_data(cls, data):
        """Unpack CAN data directly into CAN message data structure."""
        obj = cls()  # Does not call __init__
        obj.decode(data)
        obj.stamp_packet()
        return obj

    def stamp_packet(self):
        """Time most recent message was received."""
        self.stamp: Timestamp = get_monotonic_now("canbus/packet")

    def fresh(self, thresh_s: float = 0.5):
        """Returns False if the most recent message is older than ``thresh_s`` in seconds."""
        return self.age() < thresh_s

    def age(self):
        """Age of the most recent message."""
        return time.monotonic() - self.stamp.stamp


def make_amiga_rpdo1_proto(
    state_req: AmigaControlState, cmd_speed: float, cmd_ang_rate: float
) -> canbus_pb2.RawCanbusMessage:
    """Creates a canbus_pb2.RawCanbusMessage, using the AmigaRpdo1 structure and formatting, that can be sent
    directly to the canbus service to be formatted and send on the CAN bus."""
    return canbus_pb2.RawCanbusMessage(
        id=AmigaRpdo1.cob_id + DASHBOARD_NODE_ID,
        data=AmigaRpdo1(state_req=state_req, cmd_speed=cmd_speed, cmd_ang_rate=cmd_ang_rate).encode(),
    )


class AmigaRpdo1(Packet):
    """State, speed, and angular rate command (request) sent to the Amiga vehicle control unit (VCU)"""

    cob_id = 0x200

    def __init__(
        self,
        state_req: AmigaControlState = AmigaControlState.STATE_ESTOPPED,
        cmd_speed: float = 0.0,
        cmd_ang_rate: float = 0.0,
    ):
        self.format = "<Bhh"
        self.state_req = state_req
        self.cmd_speed = cmd_speed
        self.cmd_ang_rate = cmd_ang_rate

        self.stamp_packet()

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data."""
        return pack(self.format, self.state_req, int(self.cmd_speed * 1000.0), int(self.cmd_ang_rate * 1000.0))

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""
        (self.state_req, cmd_speed, cmd_ang_rate) = unpack(self.format, data)
        self.cmd_speed = cmd_speed / 1000.0
        self.cmd_ang_rate = cmd_ang_rate / 1000.0

    def __str__(self):
        return "AMIGA RPDO1 Request state {} Command speed {:0.3f} Command angular rate {:0.3f}".format(
            self.state_req, self.cmd_speed, self.cmd_ang_rate
        )


class AmigaTpdo1(Packet):
    """State, speed, and angular rate of the Amiga vehicle control unit (VCU)"""

    cob_id = 0x180

    def __init__(
        self,
        state: AmigaControlState = AmigaControlState.STATE_ESTOPPED,
        meas_speed: float = 0.0,
        meas_ang_rate: float = 0.0,
    ):
        self.format = "<Bhh"
        self.state = state
        self.meas_speed = meas_speed
        self.meas_ang_rate = meas_ang_rate

        self.stamp_packet()

    def encode(self):
        """Returns the data contained by the class encoded as CAN message data."""
        return pack(self.format, self.state, int(self.meas_speed * 1000.0), int(self.meas_ang_rate * 1000.0))

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class."""
        (self.state, meas_speed, meas_ang_rate) = unpack(self.format, data)
        self.meas_speed = meas_speed / 1000.0
        self.meas_ang_rate = meas_ang_rate / 1000.0

    def __str__(self):
        return "AMIGA TPDO1 Amiga state {} Measured speed {:0.3f} Measured angular rate {:0.3f} @ time {}".format(
            self.state, self.meas_speed, self.meas_ang_rate, self.stamp.stamp
        )


def parse_amiga_tpdo1_proto(message: canbus_pb2.RawCanbusMessage) -> Optional[AmigaTpdo1]:
    """Parses a canbus_pb2.RawCanbusMessage, IFF the message came from the dashboard and contains AmigaTpdo1
    structure, formatting, and cobid.

    Otherwise returns None.
    """
    if message.id != AmigaTpdo1.cob_id + DASHBOARD_NODE_ID:
        return None
    return AmigaTpdo1.from_can_data(message.data)
