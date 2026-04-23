from contextvars import ContextVar
from contextlib import contextmanager
from typing import Iterator

from .runner import MigrationRunner
from .registry import MigrationRegistry

_active_runner: ContextVar[MigrationRunner | None] = ContextVar(
    "active_runner", default=None
)
_active_registry: ContextVar[MigrationRegistry | None] = ContextVar(
    "active_registry", default=None
)


def get_runner() -> MigrationRunner:
    runner = _active_runner.get()
    if runner is None:
        raise RuntimeError("No active MigrationRunner.")
    return runner


def get_registry() -> MigrationRegistry:
    registry = _active_registry.get()
    if registry is None:
        raise RuntimeError("No active MigrationRegistry.")
    return registry


@contextmanager
def use_context(
    runner: MigrationRunner | None = None,
    *,
    database_url: str | None = None,
) -> Iterator[MigrationRunner]:
    active = runner or MigrationRunner(database_url=database_url)
    registry = MigrationRegistry()

    r_token = _active_runner.set(active)
    reg_token = _active_registry.set(registry)

    try:
        yield active
    finally:
        _active_runner.reset(r_token)
        _active_registry.reset(reg_token)
