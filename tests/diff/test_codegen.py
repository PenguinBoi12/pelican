import pytest
from pelican.diff.schema import SchemaColumn, SchemaTable, SchemaIndex, SchemaCheckConstraint, SchemaEnum
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
    AddEnumValue,
    RemoveEnumValue,
)
from pelican.generator import render_migration


def _col(name: str, type_: str = "VARCHAR(255)", nullable: bool = True, position: int = 0) -> SchemaColumn:
    return SchemaColumn(name=name, type=type_, nullable=nullable,
                        primary_key=False, autoincrement=False,
                        server_default=None, position=position)


def _render(ops) -> str:
    return render_migration(ops, "test_migration", 20260421000000)


def _up(ops) -> str:
    content = _render(ops)
    return content.split("def upgrade()")[1].split("def downgrade()")[0]


def _down(ops) -> str:
    content = _render(ops)
    return content.split("def downgrade()")[1]


def test_render_migration__expect_up_and_down_present() -> None:
    content = _render([])
    assert "def upgrade()" in content
    assert "def downgrade()" in content


def test_render_migration__expect_revision_in_header() -> None:
    content = _render([])
    assert "20260421000000" in content


def test_render_migration__with_no_ops__expect_pass_stubs() -> None:
    content = _render([])
    assert content.count("pass") == 2


def test_render_migration__with_add_column__expect_change_table_in_up() -> None:
    ops = [AddColumn("users", _col("email", "VARCHAR(255)", nullable=False))]
    up = _up(ops)
    assert "change_table('users')" in up
    assert "t.string('email'" in up
    assert "nullable=False" in up


def test_render_migration__with_add_column__expect_drop_in_down() -> None:
    ops = [AddColumn("users", _col("email"))]
    down = _down(ops)
    assert "t.drop('email')" in down


def test_render_migration__with_drop_column__expect_drop_in_up() -> None:
    ops = [DropColumn("users", _col("bio", "TEXT"))]
    up = _up(ops)
    assert "t.drop('bio')" in up


def test_render_migration__with_drop_column__expect_column_restored_in_down() -> None:
    ops = [DropColumn("users", _col("bio", "TEXT"))]
    down = _down(ops)
    assert "t.text('bio')" in down


def test_render_migration__with_rename__expect_rename_in_up() -> None:
    ops = [RenameColumn("users", "user_name", "username", confidence=0.95)]
    up = _up(ops)
    assert "t.rename('user_name', 'username')" in up


def test_render_migration__with_rename__expect_reverse_rename_in_down() -> None:
    ops = [RenameColumn("users", "user_name", "username", confidence=0.95)]
    down = _down(ops)
    assert "t.rename('username', 'user_name')" in down


def test_render_migration__with_create_table__expect_create_table_in_up() -> None:
    table = SchemaTable(
        "subscriptions",
        columns=[
            SchemaColumn("id", "INTEGER", False, True, True, None, 0),
            _col("name", "VARCHAR(255)", nullable=False, position=1),
        ],
    )
    ops = [CreateTable(table)]
    up = _up(ops)
    assert "create_table('subscriptions')" in up
    assert "t.string('name'" in up
    # id should be skipped (auto-added by create_table)
    assert "t.integer('id'" not in up


def test_render_migration__with_create_table__expect_drop_table_in_down() -> None:
    table = SchemaTable("subscriptions", columns=[_col("id", "INTEGER")])
    ops = [CreateTable(table)]
    down = _down(ops)
    assert "drop_table('subscriptions')" in down


def test_render_migration__with_drop_table__expect_drop_table_in_up() -> None:
    table = SchemaTable("old_table", columns=[_col("id", "INTEGER")])
    ops = [DropTable(table)]
    up = _up(ops)
    assert "drop_table('old_table')" in up


def test_render_migration__with_create_index__expect_index_in_up() -> None:
    idx = SchemaIndex("users_email_idx", ["email"], unique=True)
    ops = [CreateIndex("users", idx)]
    up = _up(ops)
    assert "t.index(['email'], name='users_email_idx', unique=True)" in up


def test_render_migration__with_create_index__expect_remove_index_in_down() -> None:
    idx = SchemaIndex("users_email_idx", ["email"], unique=True)
    ops = [CreateIndex("users", idx)]
    down = _down(ops)
    assert "t.remove_index(name='users_email_idx')" in down


def test_render_migration__with_add_enum_value__expect_comment_in_up() -> None:
    ops = [AddEnumValue("status", "banned")]
    up = _up(ops)
    assert "banned" in up
    assert "ADD VALUE" in up


def test_render_migration__with_remove_enum_value__expect_warning_in_up() -> None:
    ops = [RemoveEnumValue("status", "banned")]
    up = _up(ops)
    assert "WARNING" in up
    assert "banned" in up
