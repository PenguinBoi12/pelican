from datetime import datetime
from pathlib import Path
from .migration import Migration

TEMPLATE_DIR: Path = Path(__file__).parent / "templates"


def _get_template(template_name: str) -> str:
    return (TEMPLATE_DIR / f"{template_name}.template").read_text()


def _generate_revision() -> int:
    """Return a timestamp-based migration number (e.g. 20251003154520)."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S"))


def generate_migration(
    name: str,
    body: str | None = None,
    migration_dir: str | Path = "db/migrations/",
) -> Path:
    migration = Migration(revision=_generate_revision(), name=name)
    migration_file = Path(migration_dir) / migration.file_name
    migration_file.parent.mkdir(parents=True, exist_ok=True)

    if body is None:
        content = _get_template("migration").format(migration=migration)
    else:
        content = body

    migration_file.write_text(content)
    return migration_file


def render_migration(ops: list, name: str, revision: int) -> str:
    from .diff.codegen import _render_up, _render_down

    template = _get_template("autogenerate")
    up_body = _render_up(ops)
    down_body = _render_down(ops)
    display_name = name.replace("_", " ").capitalize()
    return template.format(
        revision=revision,
        display_name=display_name,
        up_body=up_body,
        down_body=down_body,
    )
