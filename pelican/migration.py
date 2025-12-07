from pathlib import Path
from typing import Any, Callable, TypeVar, Iterator
from dataclasses import dataclass

F = TypeVar("F", bound=Callable[..., Any])


class MigrationError(Exception):
    """Base exception for migration errors."""

    pass


class DuplicateMigrationError(MigrationError):
    """Raised when attempting to register duplicate up/down for same revision."""

    pass


@dataclass
class Migration:
    name: str
    revision: int
    up: Callable[..., Any] | None = None
    down: Callable[..., Any] | None = None
    is_applied: bool = False

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").capitalize()

    @property
    def file_name(self) -> str:
        return f"{self.revision}_{self.name}.py"


class MigrationRegistry:
    def __init__(self) -> None:
        self._migrations: dict[int, Migration] = {}

    def register_up(self, revision: int, name: str, func: F) -> None:
        migration = self._migrations.get(
            revision, Migration(revision=revision, name=name)
        )

        if not self._migrations.get(revision):
            self._migrations[revision] = migration

        if migration.up:
            raise DuplicateMigrationError(
                f"'up' migration already registered for revision {revision}"
            )
        migration.up = func
        self._order_migrations()

    def register_down(self, revision: int, name: str, func: F) -> None:
        migration = self._migrations.get(
            revision, Migration(revision=revision, name=name)
        )

        if not self._migrations.get(revision):
            self._migrations[revision] = migration

        if migration.down:
            raise DuplicateMigrationError(
                f"'down' migration already registered for revision {revision}"
            )
        migration.down = func
        self._order_migrations()

    def get_all(self) -> list[Migration]:
        return sorted(self._migrations.values(), key=lambda m: m.revision)

    def get(self, revision: int) -> Migration | None:
        return self._migrations.get(revision)

    def get_last_applied(self) -> Migration | None:
        return next((m for m in reversed(self._migrations.values()) if m.is_applied), None)

    def get_last_unapplied(self) -> Migration | None:
        return next((m for m in reversed(self._migrations.values()) if not m.is_applied), None)

    def clear(self) -> None:
        self._migrations.clear()

    def _order_migrations(self):
        self._migrations = dict(
            sorted(self._migrations.items(), key=lambda item: item[0])
        )

    def __len__(self) -> int:
        return len(self.get_all())

    def __iter__(self) -> Iterator[Migration]:
        return iter(self.get_all())


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
    from pelican import registry

    revision, name = _extract_migration_information(func)
    registry.register_up(revision, name, func)

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
    from pelican import registry

    revision, name = _extract_migration_information(func)
    registry.register_down(revision, name, func)

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
