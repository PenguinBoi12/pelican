from pathlib import Path
from typing import Callable

import pytest

from pelican.migration import (
    Migration,
    MigrationRegistry,
    DuplicateMigrationError,
    up,
    down,
)


@pytest.mark.parametrize("decorator,attr", [(up, "up"), (down, "down")])
def test_decorator_registers_migration(
    registry: MigrationRegistry,
    migration_func: Callable,
    decorator: Callable,
    attr: str,
) -> None:
    decorated = decorator(migration_func)

    assert decorated is migration_func
    assert len(registry) == 1

    migration = registry.get(1)
    assert migration is not None
    assert migration.revision == 1
    assert migration.name == "test_migration"
    assert getattr(migration, attr) is migration_func
    assert getattr(migration, f"has_{attr}")()

    opposite_attr = "down" if attr == "up" else "up"
    assert not getattr(migration, f"has_{opposite_attr}")()


@pytest.mark.parametrize("decorator,direction", [(up, "up"), (down, "down")])
def test_decorator_duplicate_registration_raises_error(
    migration_func: Callable,
    decorator: Callable,
    direction: str,
) -> None:
    decorator(migration_func)

    with pytest.raises(
        DuplicateMigrationError, match=f"'{direction}' migration already registered"
    ):
        decorator(migration_func)


def test_decorator_invalid_filename_raises_error(tmp_path: Path) -> None:
    invalid_file = tmp_path / "invalid_migration_name.py"

    func = lambda: None
    func.__globals__["__file__"] = str(invalid_file)

    with pytest.raises(ValueError, match="Invalid migration file name"):
        up(func)


@pytest.mark.parametrize(
    "name,expected_display",
    [
        ("create_users", "Create users"),
        ("add_email_column", "Add email column"),
        ("init", "Init"),
        ("create_users_and_posts_tables", "Create users and posts tables"),
    ],
)
def test_migration_display_name(name: str, expected_display: str) -> None:
    migration = Migration(name=name, revision=1)
    assert migration.display_name == expected_display


@pytest.mark.parametrize(
    "revision,name,expected_file",
    [
        (1, "create_users", "1_create_users.py"),
        (123, "add_column", "123_add_column.py"),
        (0, "initial", "0_initial.py"),
    ],
)
def test_migration_file_name(revision: int, name: str, expected_file: str) -> None:
    migration = Migration(name=name, revision=revision)
    assert migration.file_name == expected_file


def test_registry_iter_returns_sorted_by_revision(registry: MigrationRegistry) -> None:
    for revision, name in [(3, "third"), (1, "first"), (2, "second")]:
        registry.register_up(revision, name, lambda: None)

    revisions = [m.revision for m in registry]
    assert revisions == [1, 2, 3]
    assert len(registry) == 3
