farm_ng_add_protobufs(farm_ng_amiga_proto_defs
    NAMESPACE farm_ng_amiga
    INCLUDE_DIRS
      ${Sophus_PROTO_DIR}
      ${farm_ng_core_PROTO_DIR}
    PROTO_FILES
        farm_ng/canbus/canbus.proto
        farm_ng/gps/gps.proto
        farm_ng/oak/oak.proto
        farm_ng/service/service.proto
    DEPENDENCIES
      Sophus::sophus_linalg_proto_defs
      Sophus::sophus_lie_proto_defs
      farm_ng_core::farm_ng_core_proto_defs
)
