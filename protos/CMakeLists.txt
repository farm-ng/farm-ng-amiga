farm_ng_add_protobufs(farm_ng_amiga_proto_defs
    NAMESPACE farm_ng_amiga
    INCLUDE_DIRS
      ${farm_ng_core_PROTO_DIR}
    PROTO_FILES
        farm_ng/canbus/canbus.proto
        farm_ng/gps/gps.proto
        farm_ng/image/image.proto
        farm_ng/health_monitor/health_monitor.proto
        farm_ng/oak/oak.proto
        farm_ng/service/service.proto
    DEPENDENCIES
      farm_ng_core::farm_ng_core_proto_defs
)
