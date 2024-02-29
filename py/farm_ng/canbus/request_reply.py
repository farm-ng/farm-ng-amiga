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
# Python imports
import time
from enum import IntEnum
from struct import pack
from struct import unpack

from farm_ng.canbus.packet import Packet


class ReqRepOpIds(IntEnum):
    """Operation IDs for request and reply operations.

    Attributes:
        NOP (0): No operation.
        READ (1): Read operation.
        WRITE (2): Write operation.
        STORE (3): Store operation.
    """

    NOP = 0
    READ = 1
    WRITE = 2
    STORE = 3


class ReqRepValIds(IntEnum):
    """Value IDs for request and reply operations with associated properties. These IDs are used for querying and
    setting values on a dashboard.

    Attributes:
        NOP (0): No operation.
        V_MAX (10): Max linear velocity of the robot. Non-persistent value.
        FLIP_JOYSTICK (11): Invert the forward / reverse joystick input.
        MAX_TURN_RATE (20): Maximum turning rate, used at low speeds.
        MIN_TURN_RATE (21): Minimum turning rate, used at high speeds.
        MAX_ANG_ACC (23): Maximum angular acceleration.
        M10_ON - M13_ON (30-33): Enables / disables motor control signals for motors 10 to 13 (A to D), respectively.
        BATT_LO (40), BATT_HI (41): Battery voltage low/high indicators.
        TURTLE_V (45), TURTLE_W (46): Turtle mode linear and angular velocities, respectively.
        WHEEL_TRACK (50): Wheel track width. Distance between the centers of two wheels on the same axle.
        WHEEL_GEAR_RATIO (52), WHEEL_RADIUS (53): Gear ratio and radius of the wheels. Non-persistent values.
        PTO_CUR_DEV (80): Current PTO device to change settings of. Non-persistent value.
        PTO_CUR_RPM (81): Current RPM setting for the PTO device output shaft. Non-persistent value.
        PTO_MIN_RPM (82): Minimum RPM setting for the PTO device output shaft.
        PTO_MAX_RPM (83): Maximum RPM setting for the PTO device output shaft.
        PTO_DEF_RPM (84): Default RPM setting for the PTO device output shaft.
        PTO_GEAR_RATIO (85): Gear ratio for the PTO device, used to calculate the output shaft RPM.
        STEERING_GAMMA (90): Adjusts the steering response curve.

    Note:
        NP indicates a non-persistent value, meaning it cannot be stored between dashboard reboots.
    """

    NOP = 0

    V_MAX = 10  # NP
    FLIP_JOYSTICK = 11

    MAX_TURN_RATE = 20
    MIN_TURN_RATE = 21
    MAX_ANG_ACC = 23

    M10_ON = 30
    M11_ON = 31
    M12_ON = 32
    M13_ON = 33

    BATT_LO = 40
    BATT_HI = 41
    TURTLE_V = 45
    TURTLE_W = 46

    WHEEL_TRACK = 50
    WHEEL_GEAR_RATIO = 52  # NP
    WHEEL_RADIUS = 53  # NP

    PTO_CUR_DEV = 80  # NP
    PTO_CUR_RPM = 81  # NP
    PTO_MIN_RPM = 82
    PTO_MAX_RPM = 83
    PTO_DEF_RPM = 84
    PTO_GEAR_RATIO = 85

    STEERING_GAMMA = 90


class ReqRepValUnits:
    """Units for request and reply values, used in conjunction with ReqRepValIds to specify the unit of measurement
    for each value.

    Attributes:
        NOP (0): No operation, indicating no specific unit.
        NA (1): Unitless, applicable to values that do not require units.
        M (4): Meters, for distances.
        MPS (10): Meters per second, for velocities.
        RADPS (15): Radians per second, for angular velocities.
        RPM (16): Revolutions per minute, for rotational speeds.
        MS2 (20): Meters per second squared, for linear accelerations.
        RADS2 (21): Radians per second squared, for angular accelerations.
        V (25): Volts, for electrical potentials.
    """

    NOP = 0
    NA = 1
    M = 4
    MPS = 10
    RADPS = 15
    RPM = 16
    MS2 = 20
    RADS2 = 21
    V = 25


class ReqRepValFmts:
    """Data formats for request and reply values used for packing and unpacking data.

    These formats are utilized to ensure the correct interpretation and alignment of data
    when communicating with the dashboard, according to its expected data structure.

    Attributes:
        SHORT (str): Format for signed short (2 bytes) with padding to ensure alignment.
        USHORT (str): Format for unsigned short (2 bytes) with padding to ensure alignment.
        FLOAT (str): Format for floating-point numbers (4 bytes).
        BOOL (str): Format for boolean values, stored as a single byte (as an unsigned char) with padding.

    Note:
        The format strings follow the struct module's syntax, where '<' indicates little-endian byte order,
        and 'x' represents padding bytes to match the expected data size on the dashboard.
    """

    SHORT = "<h2x"
    USHORT = "<H2x"
    FLOAT = "<f"
    BOOL = "<B3x"


# Alphabetically sorted val properties.
# Each is (fmt, unit) mapping, defining the data format and unit for each ReqRepValId.
req_rep_val_props = {
    ReqRepValIds.BATT_HI: (ReqRepValFmts.FLOAT, ReqRepValUnits.V),
    ReqRepValIds.BATT_LO: (ReqRepValFmts.FLOAT, ReqRepValUnits.V),
    ReqRepValIds.FLIP_JOYSTICK: (ReqRepValFmts.BOOL, ReqRepValUnits.NA),
    ReqRepValIds.M10_ON: (ReqRepValFmts.BOOL, ReqRepValUnits.NA),
    ReqRepValIds.M11_ON: (ReqRepValFmts.BOOL, ReqRepValUnits.NA),
    ReqRepValIds.M12_ON: (ReqRepValFmts.BOOL, ReqRepValUnits.NA),
    ReqRepValIds.M13_ON: (ReqRepValFmts.BOOL, ReqRepValUnits.NA),
    ReqRepValIds.MAX_ANG_ACC: (ReqRepValFmts.FLOAT, ReqRepValUnits.RADS2),
    ReqRepValIds.MAX_TURN_RATE: (ReqRepValFmts.FLOAT, ReqRepValUnits.RADPS),
    ReqRepValIds.MIN_TURN_RATE: (ReqRepValFmts.FLOAT, ReqRepValUnits.RADPS),
    ReqRepValIds.PTO_CUR_DEV: (ReqRepValFmts.USHORT, ReqRepValUnits.NA),
    ReqRepValIds.PTO_CUR_RPM: (ReqRepValFmts.FLOAT, ReqRepValUnits.RPM),
    ReqRepValIds.PTO_DEF_RPM: (ReqRepValFmts.FLOAT, ReqRepValUnits.RPM),
    ReqRepValIds.PTO_GEAR_RATIO: (ReqRepValFmts.FLOAT, ReqRepValUnits.NA),
    ReqRepValIds.PTO_MAX_RPM: (ReqRepValFmts.FLOAT, ReqRepValUnits.RPM),
    ReqRepValIds.PTO_MIN_RPM: (ReqRepValFmts.FLOAT, ReqRepValUnits.RPM),
    ReqRepValIds.STEERING_GAMMA: (ReqRepValFmts.FLOAT, ReqRepValUnits.NA),
    ReqRepValIds.TURTLE_V: (ReqRepValFmts.FLOAT, ReqRepValUnits.MPS),
    ReqRepValIds.TURTLE_W: (ReqRepValFmts.FLOAT, ReqRepValUnits.RADPS),
    ReqRepValIds.V_MAX: (ReqRepValFmts.FLOAT, ReqRepValUnits.MPS),
    ReqRepValIds.WHEEL_GEAR_RATIO: (ReqRepValFmts.FLOAT, ReqRepValUnits.NA),
    ReqRepValIds.WHEEL_RADIUS: (ReqRepValFmts.FLOAT, ReqRepValUnits.M),
    ReqRepValIds.WHEEL_TRACK: (ReqRepValFmts.FLOAT, ReqRepValUnits.M),
}


def unpack_req_rep_value(val_id: ReqRepValIds, payload: bytes):
    """Unpacks the request/reply value from the given payload based on the value ID.

    Args:
        val_id (ReqRepValIds): The value ID.
        payload (bytes): The payload to unpack.

    Returns:
        The unpacked value.
    """
    assert len(payload) == 4, "FarmngReqRep payload should be 4 bytes"
    (fmt, unit) = req_rep_val_props[val_id]
    (value,) = unpack(fmt, payload)
    return value


class FarmngReqRep(Packet):
    """Supervisor request class, forming a parallel to the SDO protocol for CAN communication.

    This class facilitates encoding and decoding of CAN message data for request-reply
    communication with the dashboard, supporting operations like querying and setting
    device parameters.

    Attributes:
        cob_id_req (int): Command ID for request messages.
        cob_id_rep (int): Command ID for reply messages.
        format (str): The data format for encoding and decoding messages, following the
                      struct module's syntax.
    """

    cob_id_req = 0x600  # SDO command id
    cob_id_rep = 0x580  # SDO reply id
    format = "<BHx4s"

    def __init__(
        self, op_id=ReqRepOpIds.NOP, val_id=ReqRepValIds.NOP, units=ReqRepValUnits.NA, success=False, payload=bytes(4)
    ) -> None:
        self.op_id = op_id
        self.val_id = val_id
        self.units = units
        self.success = success
        self.payload = payload

        self.stamp_packet(time.monotonic())

    def encode(self):
        """Encodes the data contained by the class as CAN message data.

        Returns:
            bytes: The encoded CAN message data.
        """
        return pack(self.format, self.op_id | (self.success << 7), self.val_id | (self.units << 11), self.payload)

    def decode(self, data):
        """Decodes CAN message data and populates the values of the class.

        Args:
            data (bytes): The CAN message data to decode.
        """
        (op_and_s, v_and_u, self.payload) = unpack(self.format, data)
        self.success = op_and_s >> 7
        self.op_id = op_and_s & ~0x80
        self.units = v_and_u >> 11
        self.val_id = v_and_u & ~0xF800

    def __str__(self):
        return "supervisor req OP {} VAL {} units {} success {} payload {}".format(
            self.op_id, self.val_id, self.units, self.success, self.payload
        )
