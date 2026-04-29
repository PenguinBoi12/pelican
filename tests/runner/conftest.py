from typing import Generator

import pytest
from sqlalchemy import MetaData

from pelican.runner import MigrationRunner
from pelican._context import use_context


@pytest.fixture
def db_runner() -> Generator[MigrationRunner, None, None]:
    with use_context(database_url="sqlite:///:memory:", metadata=MetaData()) as active:
        yield active
