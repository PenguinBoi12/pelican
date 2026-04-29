from contextvars import ContextVar
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import MetaData

from .runner import MigrationRunner
from .registry import MigrationRegistry

_active_runner: ContextVar[MigrationRunner | None] = ContextVar(
    "active_runner", default=None
)
_active_registry: ContextVar[MigrationRegistry | None] = ContextVar(
    "active_registry", default=None
)


def get_runner() -> MigrationRunner:
    """Return the active `MigrationRunner` for the current context.

    ## Example

    ```python
    from pelican import get_runner

    def my_helper() -> None:
        runner = get_runner()
        runner.upgrade(migration)
    ```

    Raises `RuntimeError` if called outside of a `use_context` block.
    """
    runner = _active_runner.get()
    if runner is None:
        raise RuntimeError("No active MigrationRunner.")
    return runner


def get_registry() -> MigrationRegistry:
    """Return the active `MigrationRegistry` for the current context.

    ## Example

    ```python
    from pelican import get_registry

    def my_helper() -> None:
        registry = get_registry()
        for migration in registry:
            ...
    ```

    Raises `RuntimeError` if called outside of a `use_context` block.
    """
    registry = _active_registry.get()
    if registry is None:
        raise RuntimeError("No active MigrationRegistry.")
    return registry


@contextmanager
def use_context(
    *,
    database_url: str | None = None,
    metadata: MetaData | None = None,
) -> Iterator[MigrationRunner]:
    """Activate a runner and registry for the duration of a `with` block.

    ## Example

    ```python
    from pelican import use_context
    from pelican import loader

    with use_context(database_url="postgresql://user:password@localhost/mydb") as runner:
        registry = loader.load_migrations("db/migrations")
        for migration in registry:
            runner.upgrade(migration)
    ```
    """
    active = MigrationRunner(database_url=database_url, metadata=metadata)
    registry = MigrationRegistry()

    r_token = _active_runner.set(active)
    reg_token = _active_registry.set(registry)

    try:
        yield active
    finally:
        _active_runner.reset(r_token)
        _active_registry.reset(reg_token)
