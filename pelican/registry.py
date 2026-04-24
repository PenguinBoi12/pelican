from typing import Any, Callable, Iterator, TypeVar

from ._types import Migration, DuplicateMigrationError

F = TypeVar("F", bound=Callable[..., Any])


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

    def get_all(self) -> list[Migration]:
        return sorted(self._migrations.values(), key=lambda m: m.revision)

    def get(self, revision: int) -> Migration | None:
        return self._migrations.get(revision)

    def clear(self) -> None:
        self._migrations.clear()

    def __len__(self) -> int:
        return len(self.get_all())

    def __iter__(self) -> Iterator[Migration]:
        return iter(self.get_all())
