import importlib.metadata as importlib_metadata
import importlib
import pkgutil

# Automatically import all *_pb2 modules
for module_info in pkgutil.iter_modules(__path__, prefix=__name__ + "."):
    if module_info.name.endswith("_pb2"):
        module = importlib.import_module(module_info.name)
        globals().update({name: getattr(module, name) for name in dir(module) if not name.startswith("_")})
