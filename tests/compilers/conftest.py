import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import dialect as pg_dialect

import pelican
from pelican.compilers.postgresql import PostgreSQLCompiler
from pelican.compilers.sqlite import SQLiteCompiler


@pytest.fixture(autouse=True)
def restore_pelican_module():
    sys.modules["pelican"] = pelican
    yield


@pytest.fixture
def pg_compiler() -> PostgreSQLCompiler:
    engine = MagicMock()
    engine.dialect = pg_dialect()
    return PostgreSQLCompiler(engine)


@pytest.fixture
def sqlite_compiler() -> SQLiteCompiler:
    engine = create_engine("sqlite:///:memory:")
    return SQLiteCompiler(engine)
