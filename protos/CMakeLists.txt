farm_ng_add_protobufs(amiga_brain_api_proto_defs
    NAMESPACE amiga_brain_api
    INCLUDE_DIRS
      ${Sophus_PROTO_DIR}
    PROTO_FILES
        farm_ng/api/service.proto
        farm_ng/controller/controller.proto
        farm_ng/state_estimator/state_estimator.proto
        farm_ng/oak/oak.proto
        farm_ng/canbus/canbus.proto
    DEPENDENCIES
      Sophus::sophus_linalg_proto_defs
      Sophus::sophus_lie_proto_defs
)
