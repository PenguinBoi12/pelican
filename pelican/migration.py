from pathlib import Path
from typing import Callable, TypeVar, Any
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
    revision: int
    name: str
    up: Callable[..., Any] | None = None
    down: Callable[..., Any] | None = None

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").capitalize()

    def has_up(self) -> bool:
        return self.up is not None

    def has_down(self) -> bool:
        return self.down is not None


class MigrationRegistry:
    def __init__(self) -> None:
        self._migrations: dict[int, Migration] = {}

    def register_up(self, revision: int, name: str, func: F) -> None:
        migration = self._migrations.get(
            revision, Migration(revision=revision, name=name)
        )

        if not self._migrations.get(revision):
            self._migrations[revision] = migration

        if migration.has_up():
            raise DuplicateMigrationError(
                f"'up' migration already registered for revision {revision}"
            )
        migration.up = func

    def register_down(self, revision: int, name: str, func: F) -> None:
        migration = self._migrations.get(
            revision, Migration(revision=revision, name=name)
        )

        if not self._migrations.get(revision):
            self._migrations[revision] = migration

        if migration.has_down():
            raise DuplicateMigrationError(
                f"'down' migration already registered for revision {revision}"
            )
        migration.down = func

    def get_all(self) -> list[Migration]:
        return sorted(self._migrations.values(), key=lambda m: m.revision)

    def get(self, revision: int) -> Migration:
        return self._migrations.get(revision)

    def clear(self) -> None:
        self._migrations.clear()

    def __len__(self) -> int:
        return len(self.get_all())

    def __iter__(self):
        return iter(self.get_all())


def up() -> Callable[[F], F]:
    """Decorator to register a 'up' migration.

    ## Example

    ```python
    from pelican import migration


    @migration.up()
    def downgrade() -> None:
        ...
    ```
    """

    def decorator(func: F) -> F:
        from pelican import registry

        revision, name = _extract_migration_information(func)
        registry.register_up(revision, name, func)
        return func

    return decorator


def down() -> Callable[[F], F]:
    """Decorator to register a 'down' migration.

    ## Example

    ```python
    from pelican import migration


    @migration.down()
    def downgrade() -> None:
        ...
    ```
    """

    def decorator(func: F) -> F:
        from pelican import registry

        revision, name = _extract_migration_information(func)
        registry.register_down(revision, name, func)
        return func

    return decorator


def clear() -> None:
    """Clear all registered migrations"""
    from pelican import registry

    registry.clear()


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
