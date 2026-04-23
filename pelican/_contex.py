from contextvars import ContextVar
from pelican import MigrationRunner, MigrationRegistry

_active_runner: ContextVar[MigrationRunner | None] = ContextVar('active_runner', default=None)


def get_active_runner() -> MigrationRunner:
    runner: MigrationRunner = _active_runner.get()

    if runner is None:
        raise RuntimeError("No active MigrationRunner.")
    return runner
