import farm_ng
from farm_ng.canbus import canbus_pb2
from farm_ng.controller import controller_pb2
from farm_ng.oak import oak_pb2
from farm_ng.state_estimator import state_estimator_pb2


def test_import() -> None:
    assert farm_ng.core is not None
    assert farm_ng.core.__version__ is not None
    assert farm_ng.oak is not None
    assert farm_ng.oak.__version__ is not None

    assert canbus_pb2 is not None
    assert controller_pb2 is not None
    assert oak_pb2 is not None
    assert state_estimator_pb2 is not None
