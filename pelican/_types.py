from dataclasses import dataclass
from typing import Any, Callable


class MigrationError(Exception):
    pass


class DuplicateMigrationError(MigrationError):
    pass


class UnsupportedDialectError(MigrationError):
    pass


@dataclass
class Migration:
    name: str
    revision: int
    up: Callable[..., Any] | None = None
    down: Callable[..., Any] | None = None

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").capitalize()

    @property
    def file_name(self) -> str:
        return f"{self.revision}_{self.name}.py"
