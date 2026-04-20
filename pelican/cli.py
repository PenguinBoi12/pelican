import sys

from click import group, argument, echo, style
from pelican import registry, loader, runner


@group()
def cli() -> None:
    """Pelican - Modern database migrations for SQLAlchemy"""
    pass


@cli.command()
@argument("name", nargs=1)
def generate(name: str) -> None:
    """Generate a new migration with the given name"""
    from .generator import generate_migration

    migration_file = generate_migration(name=name)
    echo(f"Generated {migration_file}")


@cli.command()
@argument("revision", nargs=1, default=None, required=False, type=int)
def up(revision: int | None) -> None:
    """Upgrade the migration to the given or latest revision."""
    loader.load_migrations()

    if revision:
        migration = registry.get(revision)
        if not migration:
            echo(f"Migration {revision} not found.")
            sys.exit(1)
        applied = list(runner.get_applied_versions())
        if migration.revision in applied:
            echo(f"Migration {revision} is already applied.")
            return
        migrations = [migration]
    else:
        applied = list(runner.get_applied_versions())
        migrations = [m for m in registry.get_all() if m.revision not in applied]

    if not migrations:
        echo("No migration(s) to apply.")
        return

    for migration in migrations:
        runner.upgrade(migration)


@cli.command()
@argument("revision", nargs=1, default=None, required=False, type=int)
def down(revision: int | None) -> None:
    """Downgrade the migration to the given or latest revision."""
    loader.load_migrations()

    if not revision:
        applied = list(runner.get_applied_versions())
        if not applied:
            echo("No migrations have been applied.")
            return
        revision = max(applied)

    migration = registry.get(revision)
    if not migration:
        echo(f"Migration {revision} not found.")
        sys.exit(1)

    runner.downgrade(migration)


@cli.command()
def status() -> None:
    """Display the migration status."""
    loader.load_migrations()
    applied = runner.get_applied_versions()

    echo("\nMigration Status")
    echo("-" * 30)

    for migration in registry:
        is_applied = migration.revision in applied
        status_symbol = "✓" if is_applied else "○"
        color = "green" if is_applied else "yellow"

        echo(
            f"{style(status_symbol, fg=color)} {migration.revision} {migration.display_name}"
        )
    echo()


if __name__ == "__main__":
    cli()
