# Pelican

> A modern, minimal migration framework for SQLAlchemy

Pelican is a lightweight tool for managing database schema changes. It focuses on **readability, simplicity and clean developer experience.**

## Example

```python
"""20251002014707 - Create spaceships"""
from pelican import migration, create_table, drop_table


@migration.up
def upgrade():
    with create_table('spaceships') as t:
        t.string('name', nullable=False)
        t.index(['id', 'name'])


@migration.down
def downgrade():
    drop_table('spaceships')
```

## Installation

```bash
$ pip install pelican @ git+https://github.com/PenguinBoi12/pelican.git@main
```
_(Not available on PyPi yet)_

## Usage

### Create a new migration

```bash
$ pelican generate create_spaceships
```

This creates a new file under `db/migrations/` using the default template.

### Apply

```bash
$ pelican up
```

Applies all pending migration. You can also supply a **revision number** to apply migrations up to a specific revision:

```bash
$ pelican up 20251002014707
```

### Rollback migration

```bash
$ pelican down
```

Rolls back the latest migrations. You can also supply a **revision number** to roll back down to a specific revision:

```bash
pelican down 20251002014707
```

## Contributing

- Fork the repository.
- Install the development dependencies.
  ```bash
  $ pip install -e .[dev]
  ```
- Open a PR with your improvements.