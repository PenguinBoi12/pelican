from .base import DialectInspector
from .postgresql import PostgreSQLInspector
from .sqlite import SQLiteInspector

_REGISTRY: dict[str, type[DialectInspector]] = {
    "postgresql": PostgreSQLInspector,
    "sqlite": SQLiteInspector,
}


def inspector_for(dialect_name: str) -> DialectInspector:
    cls = _REGISTRY.get(dialect_name, DialectInspector)
    return cls()


__all__ = [
    "DialectInspector",
    "PostgreSQLInspector",
    "SQLiteInspector",
    "inspector_for",
]
