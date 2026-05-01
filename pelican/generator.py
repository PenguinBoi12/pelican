from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .diff.codegen import render_up, render_down
from .diff.operations import DiffOperation
from .migration import Migration

_TEMPLATE_DIR: Path = Path(__file__).parent / "templates"
_DEFAULT_MIGRATION_DIR: Path = Path("db/migrations/")


def _get_template(template_name: str) -> str:
    return (_TEMPLATE_DIR / f"{template_name}.template").read_text()


def _generate_revision() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S"))


def _render_autogenerate_body(
    ops: Sequence[DiffOperation], migration: Migration
) -> str:
    template = _get_template("autogenerate")
    return template.format(
        revision=migration.revision,
        display_name=migration.display_name,
        up_body=render_up(ops),
        down_body=render_down(ops),
    )


def generate_migration(
    name: str,
    ops: Sequence[DiffOperation] | None = None,
    migration_dir: str | Path = _DEFAULT_MIGRATION_DIR,
) -> Path:
    migration = Migration(revision=_generate_revision(), name=name)
    migration_file = Path(migration_dir) / migration.file_name
    migration_file.parent.mkdir(parents=True, exist_ok=True)

    if ops is not None:
        content = _render_autogenerate_body(ops, migration)
    else:
        content = _get_template("migration").format(migration=migration)

    migration_file.write_text(content)
    return migration_file
