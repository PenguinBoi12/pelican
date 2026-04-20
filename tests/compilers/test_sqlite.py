import pytest
from sqlalchemy import Integer, Text

from pelican.compilers.sqlite import SQLiteCompiler
from pelican.runner import _DIALECT_COMPILERS


def test_dialect_registry__expect_sqlite_registered() -> None:
    assert "sqlite" in _DIALECT_COMPILERS
    assert _DIALECT_COMPILERS["sqlite"] is SQLiteCompiler


def test_rename_column__expect_rename_sql(sqlite_compiler: SQLiteCompiler) -> None:
    ddls = list(sqlite_compiler.rename_column("users", "name", "full_name"))
    assert len(ddls) == 1
    assert "RENAME COLUMN name TO full_name" in ddls[0].statement


def test_alter_column__with_new_type__expect_not_implemented(
    sqlite_compiler: SQLiteCompiler,
) -> None:
    with pytest.raises(NotImplementedError):
        sqlite_compiler.alter_column("users", "bio", new_type=Text())


def test_alter_column__with_nullable__expect_not_implemented(
    sqlite_compiler: SQLiteCompiler,
) -> None:
    with pytest.raises(NotImplementedError):
        sqlite_compiler.alter_column("users", "email", nullable=False)
