"""Pelican - Modern database migrations for Python."""

from .migration import MigrationRegistry, registry
from .runner import MigrationRunner
from ._contex import get_active_runner
from .schema import create_table, change_table, drop_table

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pelican")
except PackageNotFoundError:
    from pelican._version import version as __version__

__all__ = [
    "__version__",
    "MigrationRunner",
    "MigrationRegistry",
    "create_table",
    "change_table",
    "drop_table",
    "get_active_runner",
    "registry",
]
