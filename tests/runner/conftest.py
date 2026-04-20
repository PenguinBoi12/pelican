import sys
from typing import Generator

import pytest
from sqlalchemy import MetaData

import pelican
from pelican.migration import MigrationRegistry
from pelican.runner import MigrationRunner


@pytest.fixture(autouse=True)
def restore_pelican_module() -> Generator[None, None, None]:
    """Keep the real pelican module in sys.modules for runner tests."""
    sys.modules["pelican"] = pelican
    yield


@pytest.fixture
def db_runner(monkeypatch: pytest.MonkeyPatch) -> MigrationRunner:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    runner = MigrationRunner()
    runner.metadata = MetaData()
    monkeypatch.setattr(pelican, "runner", runner)
    return runner


@pytest.fixture
def int_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[MigrationRegistry, None, None]:
    registry = MigrationRegistry()
    monkeypatch.setattr(pelican, "registry", registry)
    yield registry
    registry.clear()
