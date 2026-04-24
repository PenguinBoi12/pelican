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

## Passing a pre-built runner

If you need to configure the runner yourself before entering the context, pass it directly:

```python
from pelican import use_context
from pelican.runner import MigrationRunner

runner = MigrationRunner(database_url="postgresql://user:password@localhost/mydb")

with use_context(runner) as r:
    ...
```
