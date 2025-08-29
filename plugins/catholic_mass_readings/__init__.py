from __future__ import annotations

import importlib.metadata

from . import constants, models
from .usccb import USCCB

# set the version number within the package using importlib
try:
    __version__: str | None = importlib.metadata.version("catholic-mass-readings")
except importlib.metadata.PackageNotFoundError:
    # package is not installed
    __version__ = None


__all__ = ["USCCB", "__version__", "constants", "models"]
