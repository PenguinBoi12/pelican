import sys
from pathlib import Path

from click import group, argument, option, echo, style, pass_context, Context
from pelican import registry, loader, MigrationRunner

runner = MigrationRunner()


def _load_or_exit() -> None:
    if not runner.has_database_url:
        echo(
            style("Error:", fg="red")
            + " DATABASE_URL is not set. Set it in your environment or .env file.",
            err=True,
        )
        sys.exit(1)

    try:
        loader.load_migrations()
    except FileNotFoundError:
        echo(
            "No migrations directory found. "
            "Run 'pelican generate <name>' to create your first migration."
        )
        sys.exit(0)


@group()
@option("--database-url", default=None, help="Override the database URL.")
@pass_context
def cli(ctx: Context, database_url: str | None) -> None:
    """Pelican - Modern database migrations for SQLAlchemy"""
    ctx.ensure_object(dict)

    if database_url:
        runner.database_url = database_url


@cli.command()
def init() -> None:
    """Initialize a new Pelican project."""
    migrations_dir = Path("db/migrations")
    env_file = Path(".env")
    already_exists = migrations_dir.exists() and env_file.exists()

    if not migrations_dir.exists():
        migrations_dir.mkdir(parents=True)
        echo(f"Created {migrations_dir}/")
    else:
        echo(f"{migrations_dir}/ already exists, skipping.")

    if not env_file.exists():
        env_file.write_text("DATABASE_URL=sqlite:///database.db\n")
        echo(f"Created {env_file}")
    else:
        echo(f"{env_file} already exists, skipping.")

    if not already_exists:
        echo("\nNext steps:")
        echo(f"  1. Set DATABASE_URL in {env_file}")
        echo("  2. Run 'pelican generate <name>' to create your first migration")
        echo("  3. Run 'pelican up' to apply it")


@cli.command()
@argument("name", nargs=1)
def generate(name: str) -> None:
    """Generate a new migration with the given name"""
    from .generator import generate_migration

    migrations_dir = Path("db/migrations")
    dir_existed = migrations_dir.exists()

    migration_file = generate_migration(name=name)

    if not dir_existed:
        echo(f"Created {migrations_dir}/")
    echo(f"Generated {migration_file}")


@cli.command()
@argument("revision", nargs=1, default=None, required=False, type=int)
def up(revision: int | None) -> None:
    """Upgrade the migration to the given or latest revision."""
    _load_or_exit()

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
        echo(
            f"  {style('✓', fg='green')} Applied {migration.revision} {migration.display_name}"
        )


@cli.command()
@argument("revision", nargs=1, default=None, required=False, type=int)
def down(revision: int | None) -> None:
    """Downgrade the migration to the given or latest revision."""
    _load_or_exit()

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
    echo(
        f"  {style('✓', fg='green')} Rolled back {migration.revision} {migration.display_name}"
    )


@cli.command()
def status() -> None:
    """Display the migration status."""
    _load_or_exit()
    applied = set(runner.get_applied_versions())

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
