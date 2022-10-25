from farm_ng.controller import controller_pb2


class TestControllerPb2:
    def test_smoke(self) -> None:
        request = controller_pb2.MoveToGoalPoseRequest()
        print(request)
