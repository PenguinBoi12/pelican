import pytest
from pelican.diff.schema import (
    SchemaState,
    SchemaTable,
    SchemaColumn,
    SchemaIndex,
    SchemaCheckConstraint,
    SchemaEnum,
)
from pelican.diff.operations import (
    CreateTable,
    DropTable,
    AddColumn,
    DropColumn,
    RenameColumn,
    AlterColumnType,
    AlterColumnNullable,
    AlterColumnServerDefault,
    CreateIndex,
    DropIndex,
    AddCheckConstraint,
    DropCheckConstraint,
    CreateEnum,
    DropEnum,
    AddEnumValue,
    RemoveEnumValue,
)
from pelican.diff.differ import diff


def _col(
    name: str, type_: str = "VARCHAR(255)", nullable: bool = True, position: int = 0
) -> SchemaColumn:
    return SchemaColumn(
        name=name,
        type=type_,
        nullable=nullable,
        primary_key=False,
        autoincrement=False,
        server_default=None,
        position=position,
    )


def _state(*tables, enums=None) -> SchemaState:
    return SchemaState(dialect="sqlite", tables=list(tables), enums=enums or [])


def _table(name: str, *columns) -> SchemaTable:
    return SchemaTable(name=name, columns=list(columns))


def test_diff__with_identical_states__expect_no_ops() -> None:
    col = _col("name")
    state = _state(_table("users", col))
    assert diff(state, state) == []


def test_diff__with_new_table__expect_create_table() -> None:
    current = _state()
    desired = _state(_table("users", _col("id", "INTEGER")))
    ops = diff(current, desired)
    assert len(ops) == 1
    assert isinstance(ops[0], CreateTable)
    assert ops[0].table.name == "users"


def test_diff__with_dropped_table__expect_drop_table() -> None:
    current = _state(_table("users", _col("id", "INTEGER")))
    desired = _state()
    ops = diff(current, desired)
    assert len(ops) == 1
    assert isinstance(ops[0], DropTable)
    assert ops[0].table.name == "users"


def test_diff__with_added_column__expect_add_column() -> None:
    current = _state(_table("users", _col("id", "INTEGER", position=0)))
    desired = _state(
        _table(
            "users",
            _col("id", "INTEGER", position=0),
            _col("email", "VARCHAR(255)", position=1),
        )
    )
    ops = diff(current, desired)
    assert any(isinstance(o, AddColumn) and o.column.name == "email" for o in ops)


def test_diff__with_dropped_column__expect_drop_column() -> None:
    current = _state(
        _table(
            "users", _col("id", "INTEGER", position=0), _col("bio", "TEXT", position=1)
        )
    )
    desired = _state(_table("users", _col("id", "INTEGER", position=0)))
    ops = diff(current, desired)
    assert any(isinstance(o, DropColumn) and o.column.name == "bio" for o in ops)


def test_diff__with_type_change__expect_alter_column_type() -> None:
    current = _state(_table("users", _col("score", "INTEGER")))
    desired = _state(_table("users", _col("score", "DOUBLE")))
    ops = diff(current, desired)
    assert any(isinstance(o, AlterColumnType) and o.column_name == "score" for o in ops)


def test_diff__with_nullable_change__expect_alter_column_nullable() -> None:
    current = _state(_table("users", _col("email", nullable=True)))
    desired = _state(_table("users", _col("email", nullable=False)))
    ops = diff(current, desired)
    assert any(
        isinstance(o, AlterColumnNullable) and o.column_name == "email" for o in ops
    )


def test_diff__with_server_default_added__expect_alter_column_server_default() -> None:
    col_before = SchemaColumn("status", "VARCHAR(255)", True, False, False, None, 0)
    col_after = SchemaColumn(
        "status", "VARCHAR(255)", True, False, False, "'active'", 0
    )
    current = _state(_table("users", col_before))
    desired = _state(_table("users", col_after))
    ops = diff(current, desired)
    assert any(
        isinstance(o, AlterColumnServerDefault) and o.column_name == "status"
        for o in ops
    )


def test_diff__with_obvious_rename__expect_rename_column() -> None:
    before = SchemaColumn("user_name", "VARCHAR(255)", False, False, False, None, 1)
    after = SchemaColumn("username", "VARCHAR(255)", False, False, False, None, 1)
    current = _state(_table("users", _col("id", "INTEGER", position=0), before))
    desired = _state(_table("users", _col("id", "INTEGER", position=0), after))
    ops = diff(current, desired)
    renames = [o for o in ops if isinstance(o, RenameColumn)]
    assert len(renames) == 1
    assert renames[0].old_name == "user_name"
    assert renames[0].new_name == "username"
    assert renames[0].confidence >= 0.7


def test_diff__with_low_confidence_pair__expect_drop_and_add() -> None:
    before = SchemaColumn("name", "VARCHAR(255)", True, False, False, None, 0)
    after = SchemaColumn("active", "BOOLEAN", False, False, False, None, 5)
    current = _state(_table("users", before))
    desired = _state(_table("users", after))
    ops = diff(current, desired)
    assert any(isinstance(o, DropColumn) for o in ops)
    assert any(isinstance(o, AddColumn) for o in ops)
    assert not any(isinstance(o, RenameColumn) for o in ops)


def test_diff__with_new_index__expect_create_index() -> None:
    idx = SchemaIndex("users_email_idx", ["email"], unique=True)
    current = _state(_table("users", _col("email")))
    desired = SchemaState(
        dialect="sqlite",
        tables=[SchemaTable("users", columns=[_col("email")], indexes=[idx])],
    )
    ops = diff(current, desired)
    assert any(
        isinstance(o, CreateIndex) and o.index.name == "users_email_idx" for o in ops
    )


def test_diff__with_dropped_index__expect_drop_index() -> None:
    idx = SchemaIndex("users_email_idx", ["email"], unique=True)
    current = SchemaState(
        dialect="sqlite",
        tables=[SchemaTable("users", columns=[_col("email")], indexes=[idx])],
    )
    desired = _state(_table("users", _col("email")))
    ops = diff(current, desired)
    assert any(
        isinstance(o, DropIndex) and o.index.name == "users_email_idx" for o in ops
    )


def test_diff__with_new_check_constraint__expect_add_check_constraint() -> None:
    cc = SchemaCheckConstraint("price_positive", "price > 0")
    current = _state(_table("products", _col("price", "INTEGER")))
    desired = SchemaState(
        dialect="sqlite",
        tables=[
            SchemaTable(
                "products", columns=[_col("price", "INTEGER")], check_constraints=[cc]
            )
        ],
    )
    ops = diff(current, desired)
    assert any(isinstance(o, AddCheckConstraint) for o in ops)


def test_diff__with_dropped_check_constraint__expect_drop_check_constraint() -> None:
    cc = SchemaCheckConstraint("price_positive", "price > 0")
    current = SchemaState(
        dialect="sqlite",
        tables=[
            SchemaTable(
                "products", columns=[_col("price", "INTEGER")], check_constraints=[cc]
            )
        ],
    )
    desired = _state(_table("products", _col("price", "INTEGER")))
    ops = diff(current, desired)
    assert any(isinstance(o, DropCheckConstraint) for o in ops)


def test_diff__with_new_enum__expect_create_enum() -> None:
    current = _state()
    desired = SchemaState(
        dialect="postgresql", enums=[SchemaEnum("status", ["active", "inactive"])]
    )
    ops = diff(current, desired)
    assert any(isinstance(o, CreateEnum) and o.enum.name == "status" for o in ops)


def test_diff__with_dropped_enum__expect_drop_enum() -> None:
    current = SchemaState(
        dialect="postgresql", enums=[SchemaEnum("status", ["active", "inactive"])]
    )
    desired = _state()
    ops = diff(current, desired)
    assert any(isinstance(o, DropEnum) and o.enum.name == "status" for o in ops)


def test_diff__with_added_enum_value__expect_add_enum_value() -> None:
    current = SchemaState(
        dialect="postgresql", enums=[SchemaEnum("status", ["active", "inactive"])]
    )
    desired = SchemaState(
        dialect="postgresql",
        enums=[SchemaEnum("status", ["active", "inactive", "banned"])],
    )
    ops = diff(current, desired)
    assert any(isinstance(o, AddEnumValue) and o.value == "banned" for o in ops)


def test_diff__with_removed_enum_value__expect_remove_enum_value() -> None:
    current = SchemaState(
        dialect="postgresql",
        enums=[SchemaEnum("status", ["active", "inactive", "banned"])],
    )
    desired = SchemaState(
        dialect="postgresql", enums=[SchemaEnum("status", ["active", "inactive"])]
    )
    ops = diff(current, desired)
    assert any(isinstance(o, RemoveEnumValue) and o.value == "banned" for o in ops)
