import pytest
from sqlalchemy import inspect

from pelican import create_table, change_table, drop_table
from pelican.migration import Migration
from pelican.runner import MigrationRunner


def _table_exists(runner: MigrationRunner, name: str) -> bool:
    return name in inspect(runner.engine).get_table_names()


def _column_names(runner: MigrationRunner, table: str) -> list[str]:
    return [c["name"] for c in inspect(runner.engine).get_columns(table)]


def _index_names(runner: MigrationRunner, table: str) -> list[str]:
    return [i["name"] for i in inspect(runner.engine).get_indexes(table) if i["name"] is not None]


def test_upgrade__expect_version_recorded(db_runner: MigrationRunner) -> None:
    migration = Migration(name="init", revision=1)
    migration.up = lambda: None

    db_runner.upgrade(migration)

    assert 1 in list(db_runner.get_applied_versions())


def test_downgrade__expect_version_removed(db_runner: MigrationRunner) -> None:
    migration = Migration(name="init", revision=1)
    migration.up = lambda: None
    migration.down = lambda: None

    db_runner.upgrade(migration)
    db_runner.downgrade(migration)

    assert 1 not in list(db_runner.get_applied_versions())


def test_upgrade__with_multiple_migrations__expect_all_versions_tracked(db_runner: MigrationRunner) -> None:
    for rev in [1, 2, 3]:
        m = Migration(name=f"step_{rev}", revision=rev)
        m.up = lambda: None
        db_runner.upgrade(m)

    assert sorted(db_runner.get_applied_versions()) == [1, 2, 3]


def test_upgrade__with_no_up_function__expect_error(db_runner: MigrationRunner) -> None:
    migration = Migration(name="init", revision=1)
    with pytest.raises(ValueError, match="no upgrade function"):
        db_runner.upgrade(migration)


def test_downgrade__with_no_down_function__expect_error(db_runner: MigrationRunner) -> None:
    migration = Migration(name="init", revision=1)
    with pytest.raises(ValueError, match="no downgrade function"):
        db_runner.downgrade(migration)


def test_create_table__expect_table_exists(db_runner: MigrationRunner) -> None:
    with create_table("animals") as t:
        t.string("name", nullable=False)

    assert _table_exists(db_runner, "animals")


def test_create_table__expect_columns_created(db_runner: MigrationRunner) -> None:
    with create_table("animals") as t:
        t.string("name")
        t.integer("age")

    cols = _column_names(db_runner, "animals")
    assert "id" in cols
    assert "name" in cols
    assert "age" in cols


def test_create_table__with_timestamps__expect_timestamp_columns(db_runner: MigrationRunner) -> None:
    with create_table("products") as t:
        t.string("title")
        t.timestamps()

    cols = _column_names(db_runner, "products")
    assert "created_at" in cols
    assert "updated_at" in cols


def test_create_table__with_index__expect_index_exists(db_runner: MigrationRunner) -> None:
    with create_table("orders") as t:
        t.string("status")
        t.index(["status"])

    assert "orders_status_idx" in _index_names(db_runner, "orders")


def test_create_table__with_unique_index__expect_unique_flag(db_runner: MigrationRunner) -> None:
    with create_table("slugs") as t:
        t.string("value")
        t.index(["value"], unique=True)

    idxs = inspect(db_runner.engine).get_indexes("slugs")
    idx = next(i for i in idxs if i["name"] == "slugs_value_idx")
    assert idx["unique"]


def test_change_table__with_new_column__expect_column_added(db_runner: MigrationRunner) -> None:
    with create_table("jobs") as t:
        t.string("title")

    with change_table("jobs") as t:
        t.string("description")

    assert "description" in _column_names(db_runner, "jobs")


def test_change_table__with_rename__expect_column_renamed(db_runner: MigrationRunner) -> None:
    with create_table("events") as t:
        t.string("name")

    with change_table("events") as t:
        t.rename("name", "title")

    cols = _column_names(db_runner, "events")
    assert "title" in cols
    assert "name" not in cols


def test_change_table__with_drop__expect_column_removed(db_runner: MigrationRunner) -> None:
    with create_table("widgets") as t:
        t.string("color")
        t.integer("weight")

    with change_table("widgets") as t:
        t.drop("color")

    cols = _column_names(db_runner, "widgets")
    assert "color" not in cols
    assert "weight" in cols


def test_change_table__with_alter_on_sqlite__expect_not_implemented(db_runner: MigrationRunner) -> None:
    with create_table("shapes") as t:
        t.string("kind")

    with pytest.raises(NotImplementedError):
        with change_table("shapes") as t:
            t.alter("kind", nullable=True)


def test_change_table__with_alter_on_new_table__expect_error(db_runner: MigrationRunner) -> None:
    with pytest.raises(ValueError, match="alter can only be used on existing table"):
        with create_table("new_table") as t:
            t.alter("col")


def test_drop_table__expect_table_removed(db_runner: MigrationRunner) -> None:
    with create_table("temporary") as t:
        t.string("value")

    assert _table_exists(db_runner, "temporary")
    drop_table("temporary")
    assert not _table_exists(db_runner, "temporary")


def test_create_table__with_references__expect_fk_column(db_runner: MigrationRunner) -> None:
    with create_table("users") as t:
        t.string("name")

    with create_table("posts") as t:
        t.string("title")
        t.references("user")

    cols = _column_names(db_runner, "posts")
    assert "user_id" in cols


def test_upgrade_then_downgrade__expect_table_created_and_removed(db_runner: MigrationRunner) -> None:
    def upgrade() -> None:
        with create_table("posts") as t:
            t.string("title", nullable=False)
            t.text("body")
            t.timestamps()

    def downgrade() -> None:
        drop_table("posts")

    migration = Migration(name="create_posts", revision=1)
    migration.up = upgrade
    migration.down = downgrade

    db_runner.upgrade(migration)
    assert _table_exists(db_runner, "posts")
    assert 1 in list(db_runner.get_applied_versions())

    db_runner.downgrade(migration)
    assert not _table_exists(db_runner, "posts")
    assert 1 not in list(db_runner.get_applied_versions())
