from pelican.diff.schema import SchemaState, SchemaTable, SchemaColumn, SchemaIndex, SchemaEnum
from pelican.diff.operations import (
    AddColumn,
    DropColumn,
    RenameColumn,
    AlterColumnType,
    AlterColumnNullable,
    CreateIndex,
    DropIndex,
    CreateEnum,
    AddEnumValue,
)
from pelican.diff.differ import diff
from pelican.diff.validator import validate, ValidationResult


def _col(name: str, type_: str = "VARCHAR(255)", nullable: bool = True, position: int = 0) -> SchemaColumn:
    return SchemaColumn(name=name, type=type_, nullable=nullable,
                        primary_key=False, autoincrement=False,
                        server_default=None, position=position)


def _state(*tables, enums=None) -> SchemaState:
    return SchemaState(dialect="sqlite", tables=list(tables), enums=enums or [])


def _table(name: str, *columns, indexes=None) -> SchemaTable:
    return SchemaTable(name=name, columns=list(columns), indexes=indexes or [])


def test_validate__with_correct_ops__expect_valid() -> None:
    current = _state(_table("users", _col("id", "INTEGER", position=0)))
    desired = _state(_table("users", _col("id", "INTEGER", position=0), _col("email", "VARCHAR(255)", position=1)))
    ops = diff(current, desired)
    result = validate(current, desired, ops)
    assert result.is_valid is True
    assert result.discrepancies == []


def test_validate__with_no_changes__expect_valid() -> None:
    state = _state(_table("users", _col("id", "INTEGER")))
    result = validate(state, state, [])
    assert result.is_valid is True


def test_validate__with_rename__expect_valid() -> None:
    before = SchemaColumn("user_name", "VARCHAR(255)", False, False, False, None, 1)
    after = SchemaColumn("username", "VARCHAR(255)", False, False, False, None, 1)
    current = _state(_table("users", _col("id", "INTEGER", position=0), before))
    desired = _state(_table("users", _col("id", "INTEGER", position=0), after))
    ops = diff(current, desired)
    result = validate(current, desired, ops)
    assert result.is_valid is True


def test_validate__with_missing_op__expect_invalid() -> None:
    current = _state(_table("users", _col("id", "INTEGER", position=0)))
    desired = _state(_table("users", _col("id", "INTEGER", position=0), _col("email", "VARCHAR(255)", position=1)))
    result = validate(current, desired, [])
    assert result.is_valid is False
    assert len(result.discrepancies) > 0


def test_validate__with_wrong_type_in_op__expect_invalid() -> None:
    current = _state(_table("users", _col("score", "INTEGER")))
    desired = _state(_table("users", _col("score", "DOUBLE")))
    wrong_ops = [AddColumn("users", _col("score_new", "DOUBLE"))]
    result = validate(current, desired, wrong_ops)
    assert result.is_valid is False


def test_validate__add_then_drop__expect_valid() -> None:
    col_a = _col("a", "INTEGER", position=0)
    col_b = _col("b", "TEXT", position=1)
    current = _state(_table("users", col_a, col_b))
    desired = _state(_table("users", col_a))
    ops = diff(current, desired)
    result = validate(current, desired, ops)
    assert result.is_valid is True


def test_validate__does_not_mutate_current_state() -> None:
    current = _state(_table("users", _col("id", "INTEGER")))
    desired = _state(_table("users", _col("id", "INTEGER"), _col("email", "VARCHAR(255)")))
    ops = diff(current, desired)
    validate(current, desired, ops)
    assert len(current.tables[0].columns) == 1
