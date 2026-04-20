import pytest
from sqlalchemy import Integer, String, Text

from pelican.compilers.postgresql import PostgreSQLCompiler
from pelican.runner import _DIALECT_COMPILERS


def test_dialect_registry__expect_postgresql_registered():
    assert "postgresql" in _DIALECT_COMPILERS
    assert _DIALECT_COMPILERS["postgresql"] is PostgreSQLCompiler


def test_rename_column__expect_rename_sql(pg_compiler):
    ddls = list(pg_compiler.rename_column("users", "name", "full_name"))
    assert len(ddls) == 1
    assert "RENAME COLUMN name TO full_name" in ddls[0].statement


def test_alter_column__with_new_type__expect_type_sql(pg_compiler):
    ddls = list(pg_compiler.alter_column("users", "bio", new_type=Text()))
    assert len(ddls) == 1
    assert "ALTER COLUMN bio TYPE" in ddls[0].statement
    assert "TEXT" in ddls[0].statement.upper()


def test_alter_column__with_nullable_false__expect_set_not_null_sql(pg_compiler):
    ddls = list(pg_compiler.alter_column("users", "email", nullable=False))
    assert len(ddls) == 1
    assert "SET NOT NULL" in ddls[0].statement


def test_alter_column__with_nullable_true__expect_drop_not_null_sql(pg_compiler):
    ddls = list(pg_compiler.alter_column("users", "email", nullable=True))
    assert len(ddls) == 1
    assert "DROP NOT NULL" in ddls[0].statement


def test_alter_column__with_server_default__expect_set_default_sql(pg_compiler):
    ddls = list(pg_compiler.alter_column("users", "active", server_default="true"))
    assert len(ddls) == 1
    assert "SET DEFAULT true" in ddls[0].statement


def test_alter_column__with_multiple_changes__expect_multiple_statements(pg_compiler):
    ddls = list(
        pg_compiler.alter_column("users", "score", new_type=Integer(), nullable=False)
    )
    assert len(ddls) == 2


def test_alter_column__with_no_changes__expect_error(pg_compiler):
    with pytest.raises(ValueError, match="requires at least one change"):
        pg_compiler.alter_column("users", "name")
