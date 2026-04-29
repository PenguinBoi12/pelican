from pathlib import Path
from typing import Any, Callable, TypeVar

from ._types import Migration, MigrationError, DuplicateMigrationError
from .registry import MigrationRegistry
from ._context import get_registry

F = TypeVar("F", bound=Callable[..., Any])

__all__ = [
    "Migration",
    "MigrationError",
    "DuplicateMigrationError",
    "MigrationRegistry",
]


def up(func: F) -> F:
    """Decorator to register an 'up' migration.

    ## Example

    ```python
    from pelican import migration


    @migration.up
    def upgrade() -> None:
        ...
    ```
    """
    revision, name = _extract_migration_information(func)
    get_registry().register_up(revision, name, func)
    return func


def down(func: F) -> F:
    """Decorator to register a 'down' migration.

    ## Example

    ```python
    from pelican import migration


    @migration.down
    def downgrade() -> None:
        ...
    ```
    """
    revision, name = _extract_migration_information(func)
    get_registry().register_down(revision, name, func)
    return func


def _extract_migration_information(func: F) -> tuple[int, str]:
    file_name = Path(func.__globals__.get("__file__", "")).name
    base_name = Path(file_name).stem

    try:
        revision_str, name = base_name.split("_", 1)
        revision = int(revision_str)
    except ValueError:
        raise ValueError(
            f"Invalid migration file name '{file_name}'. "
            "Expected format: <revision>_<name>.py"
        )
    return revision, name
