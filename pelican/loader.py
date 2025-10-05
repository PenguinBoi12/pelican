import os
import sys
import importlib.util
from pathlib import Path
from pelican import migration


def discover_migration_files(migrations_dir: Path) -> list[Path]:
    """Return a sorted list of migration files in the specified directory."""
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    migrations = [Path(f) for f in os.listdir(migrations_dir) if f.endswith(".py")]
    migrations.sort(reverse=True)

    return migrations


def load_migration_file(file_path: Path) -> None:
    """Load a single migration file into the system."""
    module_name = file_path.stem

    if spec := importlib.util.spec_from_file_location(module_name, file_path):
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        if spec.loader:
            spec.loader.exec_module(module)


def load_migrations(migrations_dir: str | Path = "db/migrations") -> None:
    """Load and register all migration files from the specified directory."""
    migrations_path = Path(migrations_dir)
    migration.clear()

    for file_path in discover_migration_files(migrations_path):
        load_migration_file(migrations_path / file_path)
