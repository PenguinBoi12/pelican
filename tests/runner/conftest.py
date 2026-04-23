from typing import Generator

import pytest
from sqlalchemy import MetaData

from pelican.migration import MigrationRegistry
from pelican.runner import MigrationRunner
from pelican._context import use_context


@pytest.fixture
def db_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[MigrationRunner, None, None]:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    runner = MigrationRunner()
    runner.metadata = MetaData()
    with use_context(runner) as active:
        yield active
