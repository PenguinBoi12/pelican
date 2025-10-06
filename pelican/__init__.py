"""Pelican - Modern database migrations for Python."""

from .migration import MigrationRegistry
from .runner import MigrationRunner
from .operations import create_table, change_table, drop_table

__version__ = "1.0.0-alpha"

__all__ = [
    "create_table",
    "change_table",
    "drop_table",
]

registry: MigrationRegistry = MigrationRegistry()
runner: MigrationRunner = MigrationRunner()
