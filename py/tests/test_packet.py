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
import time

import pytest
from farm_ng.canbus import amiga_v6_pb2
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.packet import AmigaControlState
from farm_ng.canbus.packet import AmigaRpdo1
from farm_ng.canbus.packet import AmigaTpdo1
from farm_ng.canbus.packet import BugDispenserRpdo3
from farm_ng.canbus.packet import BugDispenserTpdo3
from farm_ng.canbus.packet import MotorControllerStatus
from farm_ng.canbus.packet import MotorState
from farm_ng.canbus.packet import PendantButtons
from farm_ng.canbus.packet import PendantState


@pytest.fixture
def amiga_rpdo1_instance():
    return AmigaRpdo1(
        state_req=AmigaControlState.STATE_AUTO_ACTIVE, cmd_speed=2.0, cmd_ang_rate=1.0, pto_bits=0x0A, hbridge_bits=0x05
    )


@pytest.fixture
def amiga_tpdo1_instance():
    return AmigaTpdo1(
        state=AmigaControlState.STATE_AUTO_READY, meas_speed=3.0, meas_ang_rate=1.5, pto_bits=0x01, hbridge_bits=0x02
    )


@pytest.fixture
def pendant_state_instance():
    return PendantState(x=0.5, y=-0.5, buttons=PendantButtons.PAUSE | PendantButtons.BRAKE)


@pytest.fixture
def motor_state_instance():
    return MotorState(
        id=1,
        status=MotorControllerStatus.RUN,
        rpm=1000,
        voltage=24.0,
        current=1.5,
        temperature=25,
        timestamp=time.monotonic(),
    )


def test_amiga_rpdo1_encode_decode(amiga_rpdo1_instance):
    encoded = amiga_rpdo1_instance.encode()
    decoded_instance = AmigaRpdo1()
    decoded_instance.decode(encoded)

    assert amiga_rpdo1_instance.state_req == decoded_instance.state_req
    assert amiga_rpdo1_instance.cmd_speed == decoded_instance.cmd_speed
    assert amiga_rpdo1_instance.cmd_ang_rate == decoded_instance.cmd_ang_rate
    assert amiga_rpdo1_instance.pto_bits == decoded_instance.pto_bits
    assert amiga_rpdo1_instance.hbridge_bits == decoded_instance.hbridge_bits


def test_amiga_tpdo1_to_from_proto(amiga_tpdo1_instance):
    proto = amiga_tpdo1_instance.to_proto()
    assert isinstance(proto, amiga_v6_pb2.AmigaTpdo1)

    from_proto_instance = AmigaTpdo1.from_proto(proto)
    assert from_proto_instance.state == amiga_tpdo1_instance.state
    assert from_proto_instance.meas_speed == amiga_tpdo1_instance.meas_speed
    assert from_proto_instance.meas_ang_rate == amiga_tpdo1_instance.meas_ang_rate
    assert from_proto_instance.pto_bits == amiga_tpdo1_instance.pto_bits
    assert from_proto_instance.hbridge_bits == amiga_tpdo1_instance.hbridge_bits


def test_pendant_state_encode_decode(pendant_state_instance):
    encoded = pendant_state_instance.encode()
    decoded_instance = PendantState()
    decoded_instance.decode(encoded)

    # Approx for floating point comparison after float -> int -> float conversion
    assert pendant_state_instance.x == pytest.approx(decoded_instance.x, rel=1e-3)
    assert pendant_state_instance.y == pytest.approx(decoded_instance.y, rel=1e-3)
    assert pendant_state_instance.buttons == decoded_instance.buttons

    # Test the is_button_pressed method
    assert pendant_state_instance.is_button_pressed(PendantButtons.PAUSE)
    assert pendant_state_instance.is_button_pressed(PendantButtons.BRAKE)
    assert not pendant_state_instance.is_button_pressed(PendantButtons.CRUISE)
    assert not pendant_state_instance.is_button_pressed(PendantButtons.LEFT)


def test_motor_state_to_from_proto(motor_state_instance):
    proto = motor_state_instance.to_proto()
    assert isinstance(proto, canbus_pb2.MotorState)

    from_proto_instance = MotorState.from_proto(proto)
    assert from_proto_instance.id == motor_state_instance.id
    assert from_proto_instance.status == motor_state_instance.status
    assert from_proto_instance.rpm == motor_state_instance.rpm
    assert from_proto_instance.voltage == motor_state_instance.voltage
    assert from_proto_instance.current == motor_state_instance.current
    assert from_proto_instance.temperature == motor_state_instance.temperature


@pytest.fixture
def bug_dispenser_rpdo3_instance():
    return BugDispenserRpdo3(rate1=10.58, rate2=18.3462, rate3=0.559)


@pytest.fixture
def bug_dispenser_tpdo3_instance():
    return BugDispenserTpdo3(rate1=1, counter1=138, rate2=15, counter2=200, rate3=12, counter3=255)


def test_bug_dispenser_rpdo3_encode_decode(bug_dispenser_rpdo3_instance):
    encoded = bug_dispenser_rpdo3_instance.encode()
    decoded_instance = BugDispenserRpdo3()
    decoded_instance.decode(encoded)

    assert bug_dispenser_rpdo3_instance.rate1 == pytest.approx(decoded_instance.rate1, rel=1e-1)
    assert bug_dispenser_rpdo3_instance.rate2 == pytest.approx(decoded_instance.rate2, rel=1e-1)
    assert bug_dispenser_rpdo3_instance.rate3 == pytest.approx(decoded_instance.rate3, rel=1e-1)


def test_bug_dispenser_rpdo3_invalid_rate():
    with pytest.raises(ValueError):
        BugDispenserRpdo3(rate1=30.0).encode()


def test_bug_dispenser_tpdo3_encode_decode(bug_dispenser_tpdo3_instance):
    encoded = bug_dispenser_tpdo3_instance.encode()
    decoded_instance = BugDispenserTpdo3()
    decoded_instance.decode(encoded)

    assert bug_dispenser_tpdo3_instance.rate1 == pytest.approx(decoded_instance.rate1, rel=1e-1)
    assert bug_dispenser_tpdo3_instance.counter1 == decoded_instance.counter1
    assert bug_dispenser_tpdo3_instance.rate2 == pytest.approx(decoded_instance.rate2, rel=1e-1)
    assert bug_dispenser_tpdo3_instance.counter2 == decoded_instance.counter2
    assert bug_dispenser_tpdo3_instance.rate3 == pytest.approx(decoded_instance.rate3, rel=1e-1)
    assert bug_dispenser_tpdo3_instance.counter3 == decoded_instance.counter3


def test_bug_dispenser_tpdo3_invalid_rate():
    with pytest.raises(ValueError):
        BugDispenserTpdo3(rate1=300).encode()


def test_bug_dispenser_tpdo3_invalid_counter():
    with pytest.raises(ValueError):
        BugDispenserTpdo3(counter1=300).encode()


if __name__ == "__main__":
    pytest.main()
