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
