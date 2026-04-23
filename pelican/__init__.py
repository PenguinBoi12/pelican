"""Pelican - Modern database migrations for Python."""

from .runner import MigrationRunner
from ._context import use_context
from .schema import create_table, change_table, drop_table

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pelican")
except PackageNotFoundError:
    from pelican._version import version as __version__

__all__ = [
    "__version__",
    "MigrationRunner",
    "use_context",
    "create_table",
    "change_table",
    "drop_table",
]
