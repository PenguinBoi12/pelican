import sys
from pathlib import Path

import click
from click import group, argument, option, echo, style, pass_context, Context

from pelican._context import use_context, get_runner
from pelican.runner import MigrationRunner
from pelican.registry import MigrationRegistry
from pelican import loader


def _load_or_exit() -> tuple[MigrationRunner, MigrationRegistry]:
    runner = get_runner()

    if not runner.has_database_url:
        echo(
            style("Error:", fg="red")
            + " DATABASE_URL is not set. Set it in your environment or .env file.",
            err=True,
        )
        sys.exit(1)

    try:
        registry = loader.load_migrations()
    except FileNotFoundError:
        echo(
            "No migrations directory found. "
            "Run 'pelican generate <name>' to create your first migration."
        )
        sys.exit(0)

    return runner, registry


@group()
@option("--database-url", default=None, help="Override the database URL.")
@pass_context
def cli(ctx: Context, database_url: str | None) -> None:
    """Pelican - Modern database migrations for SQLAlchemy"""
    ctx.with_resource(use_context(database_url=database_url))


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
    runner, registry = _load_or_exit()

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
    runner, registry = _load_or_exit()

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
    runner, registry = _load_or_exit()

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


def _confirm_renames(renames: list) -> list:
    confirmed = []
    for rename in renames:
        if click.confirm(
            f"Did you rename '{rename.old_name}' to '{rename.new_name}'"
            f" in table '{rename.table_name}'?",
            default=False,
        ):
            confirmed.append(rename)
        else:
            confirmed.extend(rename.to_drop_add())
    return confirmed


@cli.command()
@argument("name", nargs=1)
@option(
    "--models",
    "models_path",
    required=True,
    help="Import path to your models module (e.g. myapp.models)",
)
@option(
    "--force",
    is_flag=True,
    default=False,
    help="Write migration even if validation finds discrepancies",
)
def autogenerate(name: str, models_path: str, force: bool) -> None:
    """Autogenerate a migration by diffing your models against the live database."""
    from .diff.discovery import load_target_metadata
    from .diff.extractor import extract_from_metadata
    from .diff.inspector import introspect_live_db
    from .diff.differ import diff
    from .diff.validator import validate
    from .generator import generate_migration

    db_runner = get_runner()
    if not db_runner.has_database_url:
        echo(
            style("Error:", fg="red")
            + " DATABASE_URL is not set. Set it in your environment or .env file.",
            err=True,
        )
        sys.exit(1)

    try:
        metadata = load_target_metadata(models_path)
    except (ImportError, ValueError) as e:
        echo(style("Error:", fg="red") + f" {e}", err=True)
        sys.exit(1)

    desired = extract_from_metadata(metadata, db_runner.engine.dialect)
    current = introspect_live_db(db_runner.engine)
    diff_result = diff(current, desired)

    if not diff_result:
        echo("No changes detected.")
        return

    ops = diff_result.ops + _confirm_renames(diff_result.renames)

    result = validate(current, desired, ops)
    if not result.is_valid:
        echo(style("✗", fg="red") + " Validation failed. Migration not written.")
        echo("  After applying, the following would still differ from your models:")
        for disc in result.discrepancies:
            echo(f"    {disc}")
        if not force:
            echo(f"\n  Run with {style('--force', bold=True)} to write anyway.")
            sys.exit(1)
        echo(style("  Writing anyway (--force).", fg="yellow"))

    echo("\nDetecting changes...\n")
    for op in ops:
        echo(f"  {op}")

    migration_file = generate_migration(name, ops=ops)
    echo(f"\nGenerated {migration_file}")
    echo(
        style("Tip:", fg="cyan") + " Review the migration before running 'pelican up'."
    )


if __name__ == "__main__":
    cli()
