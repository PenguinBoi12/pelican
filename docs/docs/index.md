# Pelican

<div align="center" markdown>

*A modern, minimal migration framework for SQLAlchemy*

[![Tests](https://github.com/PenguinBoi12/pelican/actions/workflows/tests.yml/badge.svg)](https://github.com/PenguinBoi12/pelican/actions/workflows/tests.yml)
[![CodeQL Advanced](https://github.com/PenguinBoi12/pelican/actions/workflows/codeql.yml/badge.svg)](https://github.com/PenguinBoi12/pelican/actions/workflows/codeql.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/pelican-migration)](https://pypi.org/project/pelican-migration/)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/PenguinBoi12/pelican/badge)](https://securityscorecards.dev/viewer/?uri=github.com/PenguinBoi12/pelican)


**[Documentation](https://penguinboi12.github.io/pelican)** •
**[Source Code](https://github.com/PenguinBoi12/pelican)**

</div>

---

Pelican is a lightweight tool for managing database schema changes. It focuses on **readability, simplicity and clean developer experience.**

```python
"""20251002014707 - Create spaceships"""
from pelican import migration, create_table, drop_table


@migration.up
def upgrade():
    with create_table('spaceships') as t:
        t.string('name', nullable=False)
        t.integer('crew_capacity', default=1)
        t.timestamps()


@migration.down
def downgrade():
    drop_table('spaceships')
```

=== "Installation"
    
    Create and activate a [virtual environment](https://docs.python.org/3/library/venv.html) and install Pelican:

    ```bash
    pip install pelican-migration
    ```

=== "Configuration"

    Pelican requires a `DATABASE_URL` environment variable:

    ```bash
    export DATABASE_URL=postgresql://user:password@localhost/mydb
    ```

    You can also pass it directly to any command:

    ```bash
    pelican --database-url postgresql://user:password@localhost/mydb up
    ```

    Supported databases: [**SQLite**](reference/compilers/#pelican.compilers.sqlite.SQLiteCompiler), [**PostgreSQL**](reference/compilers/#pelican.compilers.postgresql.PostgreSQLCompiler).

=== "Usage"

    **Generate a migration**

    ```bash
    pelican generate create_spaceships
    ```

    Creates `db/migrations/<timestamp>_create_spaceships.py` from the default template.

    **Apply migrations**

    ```bash
    pelican up          # apply all pending migrations
    pelican up 123      # apply a specific revision
    ```

    **Roll back**

    ```bash
    pelican down        # roll back the latest applied migration
    pelican down 123    # roll back a specific revision
    ```

    **Check status**

    ```bash
    pelican status
    ```

    ```
    Migration Status
    ------------------------------
    ✓ 20251001120000 Create users
    ✓ 20251002014707 Create spaceships
    ○ 20251003090000 Add crew manifest
    ```

## Schema DSL

### create_table

```python
from pelican import create_table

with create_table('spaceships') as t:
    t.string('name', nullable=False)
    t.integer('crew_capacity', default=1)
    t.boolean('active', default=True)
    t.text('description')
    t.references('user')        # adds user_id FK → users.id
    t.timestamps()              # adds created_at and updated_at
    t.index(['name'], unique=True)
```

### change_table

```python
from pelican import change_table

with change_table('spaceships') as t:
    t.string('designation')         # add column
    t.rename('name', 'full_name')   # rename column
    t.drop('description')           # drop column
    t.remove_index(['full_name'])    # drop index
```

### drop_table

```python
from pelican import drop_table

drop_table('spaceships')
```

### Column types

| Method | SQLAlchemy type |
|---|---|
| `t.integer(name)` | `Integer` |
| `t.float(name)` | `Float` |
| `t.double(name)` | `Double` |
| `t.boolean(name)` | `Boolean` |
| `t.string(name, length=255)` | `String` |
| `t.text(name)` | `Text` |
| `t.datetime(name)` | `DateTime` |
| `t.timestamps()` | `created_at` + `updated_at` |
| `t.references(model)` | `Integer` FK to `<model_plural>.id` |

All methods accept standard SQLAlchemy column kwargs (`nullable`, `default`, `index`, etc.).

## Contributing

- Fork the repository.
- Install the development dependencies:
  ```bash
  pip install -e ".[dev]"
  ```
- Open a PR with your improvements.
