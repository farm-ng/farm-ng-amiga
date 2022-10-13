import farm_ng


def test_import() -> None:
    assert farm_ng.core is not None
    assert farm_ng.core.__version__ is not None
    assert farm_ng.oak is not None
    assert farm_ng.oak.__version__ is not None
