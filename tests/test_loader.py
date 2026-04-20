from pathlib import Path

import pytest

from pelican.loader import discover_migration_files, load_migration_file, load_migrations
from pelican.migration import MigrationRegistry


_MIGRATION_TEMPLATE = """\
from pelican.migration import up, down

@up
def upgrade():
    pass

@down
def downgrade():
    pass
"""


# --- discover_migration_files ---


def test_discover_migration_files__expect_py_files_returned(tmp_path):
    (tmp_path / "1_create_users.py").write_text("")
    (tmp_path / "2_add_email.py").write_text("")

    files = discover_migration_files(tmp_path)

    assert len(files) == 2
    assert all(str(f).endswith(".py") for f in files)


def test_discover_migration_files__with_non_py_files__expect_ignored(tmp_path):
    (tmp_path / "1_create_users.py").write_text("")
    (tmp_path / "README.md").write_text("")
    (tmp_path / "notes.txt").write_text("")

    files = discover_migration_files(tmp_path)

    assert len(files) == 1


def test_discover_migration_files__with_missing_directory__expect_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_migration_files(tmp_path / "nonexistent")


# --- load_migration_file ---


def test_load_migration_file__expect_migration_registered(tmp_path, registry):
    migration_file = tmp_path / "1_create_users.py"
    migration_file.write_text(_MIGRATION_TEMPLATE)

    load_migration_file(migration_file)

    migration = registry.get(1)
    assert migration is not None
    assert migration.name == "create_users"
    assert migration.up is not None
    assert migration.down is not None


# --- load_migrations ---


def test_load_migrations__expect_all_files_registered(tmp_path, registry):
    for rev, name in [(1, "create_users"), (2, "add_email"), (3, "create_posts")]:
        (tmp_path / f"{rev}_{name}.py").write_text(_MIGRATION_TEMPLATE)

    load_migrations(tmp_path)

    assert len(registry) == 3
    assert {m.revision for m in registry} == {1, 2, 3}


def test_load_migrations__expect_registry_cleared_before_load(tmp_path, registry):
    registry.register_up(99, "stale", lambda: None)

    (tmp_path / "1_create_users.py").write_text(_MIGRATION_TEMPLATE)

    load_migrations(tmp_path)

    assert registry.get(99) is None
    assert registry.get(1) is not None


def test_load_migrations__with_empty_directory__expect_empty_registry(tmp_path, registry):
    load_migrations(tmp_path)

    assert len(registry) == 0


def test_load_migrations__with_missing_directory__expect_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_migrations(tmp_path / "nonexistent")
