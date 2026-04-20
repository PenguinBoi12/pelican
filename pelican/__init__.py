"""Pelican - Modern database migrations for Python."""

from .migration import MigrationRegistry
from .runner import MigrationRunner
from .schema import create_table, change_table, drop_table

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pelican")
except PackageNotFoundError:
    from pelican._version import version as __version__

__all__ = [
    "__version__",
    "create_table",
    "change_table",
    "drop_table",
]

registry: MigrationRegistry = MigrationRegistry()
runner: MigrationRunner = MigrationRunner()
