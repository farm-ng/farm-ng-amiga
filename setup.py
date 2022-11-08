# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
from farm_ng.package.commands import BuildProtosDevelop
from farm_ng.package.commands import BuildProtosEggInfo
from farm_ng.package.commands import BuildProtosInstall
from farm_ng.package.commands import CleanFilesCommand
from setuptools import setup

PROTO_ROOT: str = "protos"
PACKAGE_ROOT: str = "py"

BuildProtosDevelop.user_options.append(("proto-root=", None, PROTO_ROOT))
BuildProtosDevelop.user_options.append(("package-root=", None, PACKAGE_ROOT))

BuildProtosInstall.user_options.append(("proto-root=", None, PROTO_ROOT))
BuildProtosInstall.user_options.append(("package-root=", None, PACKAGE_ROOT))

BuildProtosEggInfo.user_options.append(("proto-root=", None, PROTO_ROOT))
BuildProtosEggInfo.user_options.append(("package-root=", None, PACKAGE_ROOT))

CleanFilesCommand.user_options.append(("package-root=", None, PACKAGE_ROOT))

setup(
    cmdclass={
        "install": BuildProtosInstall,
        "develop": BuildProtosDevelop,
        "egg_info": BuildProtosEggInfo,
        "clean": CleanFilesCommand,
    }
)
