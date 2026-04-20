import sys

import pytest
from sqlalchemy.dialects.postgresql import dialect as pg_dialect
from unittest.mock import MagicMock

import pelican
from pelican.compilers.postgresql import PostgreSQLCompiler


@pytest.fixture(autouse=True)
def restore_pelican_module():
    sys.modules["pelican"] = pelican
    yield


@pytest.fixture
def pg_compiler() -> PostgreSQLCompiler:
    engine = MagicMock()
    engine.dialect = pg_dialect()
    return PostgreSQLCompiler(engine)
