from click import group, argument, echo, style
from pelican import migration, loader, runner

DEFAULT_MIGRATION_DIR: str = "db/migrations/"


@group()
def cli() -> None:
    """Pelican - Modern database migrations for SQLAlchemy"""
    pass


@cli.command()
@argument("name", nargs=1)
def generate(name: str) -> None:
    from .generator import generate_migration

    migration_file = generate_migration(name=name)
    echo(f"Generated {migration_file}")


@cli.command()
def up() -> None:
    loader.load_migrations()


@cli.command()
def down() -> None:
    loader.load_migrations()


@cli.command()
def status() -> None:
    """Display the migration status."""
    loader.load_migrations(DEFAULT_MIGRATION_DIR)

    # TODO: find applied migrations
    applied: list[str] = []

    echo("\nMigration Status")
    echo("-" * 30)

    for m in migration.registry.get_all():
        is_applied = str(m.revision) in applied
        status_symbol = "✓" if is_applied else "○"
        color = "green" if is_applied else "yellow"

        echo(f"{style(status_symbol, fg=color)} {m.revision} {m.display_name}")
    echo()


if __name__ == "__main__":
    cli()
