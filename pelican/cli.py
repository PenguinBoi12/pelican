from click import group, argument

DEFAULT_MIGRATION_DIR: str = 'db/migrations/'


@group()
def cli() -> None:
    pass


@cli.command()
@argument('name', nargs=1)
@argument('path', default=DEFAULT_MIGRATION_DIR, nargs=1)
def generate(name: str, path: str) -> None:
    from .generator import generate_migration

    migration_file = generate_migration(path, name)
    print(f"Generated {migration_file}")


@cli.command()
def up() -> None:
    from .migration import get_migrations

    for migration in get_migrations(DEFAULT_MIGRATION_DIR):
        print(migration)


@cli.command()
def down() -> None:
    from .migration import get_migrations

    for migration in get_migrations(DEFAULT_MIGRATION_DIR):
        print(migration)


@cli.command()
def status() -> None:
    from .migration import get_migrations

    for migration in get_migrations(DEFAULT_MIGRATION_DIR):
        print(migration)



if __name__ == '__main__':
    cli()
