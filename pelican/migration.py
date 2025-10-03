import os
from typing import Callable, TypeVar, Any

F = TypeVar("F", bound=Callable[..., Any])


_MIGRATIONS: dict[int, dict[str, Callable[..., Any]]] = {}


class MigrationError(Exception):
	pass


def up(version: int) -> Callable[[F], F]:
    """Decorator for 'up' migration"""
    def decorator(func: F) -> F:
        if version not in _MIGRATIONS:
            _MIGRATIONS[version] = {}
        _MIGRATIONS[version]['up'] = func
        return func
    return decorator


def down(version: int) -> Callable[[F], F]:
    """Decorator for 'down' migration"""
    def decorator(func: F) -> F:
        if version not in _MIGRATIONS:
            _MIGRATIONS[version] = {}
        _MIGRATIONS[version]['down'] = func
        return func
    return decorator


def get_migrations(path: str) -> list[str]:
    migrations = [f for f in os.listdir(path) if f.endswith('.py')]
    migrations.sort(reverse=True)
    return migrations
