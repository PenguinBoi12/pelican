from pathlib import Path
from typing import Callable, Generator

import pytest

from pelican.migration import MigrationRegistry
from pelican._context import _active_registry


@pytest.fixture(autouse=True)
def use_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def registry() -> Generator[MigrationRegistry, None, None]:
    registry_ = MigrationRegistry()
    token = _active_registry.set(registry_)
    yield registry_
    _active_registry.reset(token)
    registry_.clear()


@pytest.fixture
def migration_file(tmp_path: Path) -> Path:
    file = tmp_path / "001_test_migration.py"
    file.write_text("")
    return file


@pytest.fixture
def migration_func(migration_file: Path) -> Callable:
    def func() -> None:
        pass

    func.__globals__["__file__"] = str(migration_file)
    return func


@pytest.fixture(scope="session", autouse=True)
def cleanup_stray_databases() -> Generator:
    db_path = Path("database.db")

    if db_path.exists():
        db_path.unlink()

    yield

    if db_path.exists():
        db_path.unlink()
