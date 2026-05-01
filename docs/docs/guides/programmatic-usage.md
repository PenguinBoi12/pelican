# Programmatic usage

Pelican can be used directly from Python code instead of the CLI. The entry point is `use_context`, which sets up an active runner and registry for the duration of a `with` block.

## Basic example

```python
from pelican import use_context
from pelican import loader

with use_context(database_url="postgresql://user:password@localhost/mydb") as runner:
    registry = loader.load_migrations("db/migrations")
    for migration in registry:
        runner.upgrade(migration)
```

`use_context` creates a `MigrationRunner` from the given URL (or falls back to the `DATABASE_URL` environment variable), and makes both the runner and a fresh registry available via context for the duration of the block.

## Database URL

Pass the database URL directly to `use_context`:

```python
from pelican import use_context

with use_context(database_url="postgresql://user:password@localhost/mydb") as runner:
    ...
```

If `database_url` is omitted, Pelican falls back to the `DATABASE_URL` environment variable. A `RuntimeError` is raised if neither is set.

## Custom metadata

By default, `MigrationRunner` uses `SQLModel.metadata`. If you manage your own `MetaData` instance, pass it directly:

```python
from sqlalchemy import MetaData
from pelican import use_context

my_metadata = MetaData()

with use_context(database_url="postgresql://user:password@localhost/mydb", metadata=my_metadata) as runner:
    ...
```
