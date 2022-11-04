# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
# Version variable
import sys

if sys.version_info >= (3, 8):  # pragma: >=3.8 cover
    import importlib.metadata as importlib_metadata
else:  # pragma: <3.8 cover
    import importlib_metadata

__version__ = importlib_metadata.version("farm_ng_amiga")
