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
@argument("revision", nargs=1, default=None, type=int)
def up(revision: int | None) -> None:
    """Upgrade the migration to the given or latest revision."""
    loader.load_migrations()
    runner.upgrade(registry.get(revision))


@cli.command()
@argument("revision", nargs=1, default=None, type=int)
def down(revision: int | None) -> None:
    """Downgrade the migration to the given or latest revision."""
    loader.load_migrations()
    runner.downgrade(registry.get(revision))


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
