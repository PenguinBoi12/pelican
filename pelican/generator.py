from datetime import datetime
from pathlib import Path

TEMPLATE_DIR: Path = Path(__file__).parent / "templates"


def _get_template(template_name: str) -> str:
    return (TEMPLATE_DIR / f"{template_name}.template").read_text()


def generate_number() -> str:
    """Return a timestamp-based migration number (e.g. 20251003154520)."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def generate_migration(
    migration_dir: str | Path = "db/migrations/", name: str | None = None
) -> Path:
    migration_number = generate_number()
    migration_file = Path(migration_dir) / f"{migration_number}_{name}.py"

    content = _get_template("migration").format(
        migration_number=migration_number, migration_file=migration_file
    )

    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text(content)

    return migration_file
