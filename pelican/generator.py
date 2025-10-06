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
    migration_dir: str | Path = "db/migrations/", name: str | None = None
) -> Path:
    migration = Migration(revision=_generate_revision(), name=name)
    migration_file = Path(migration_dir) / migration.file_name

    content = _get_template("migration").format(migration=migration)

    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text(content)

    return migration_file
