from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.types import TypeEngine

from ..schema import SchemaEnum


class DialectInspector:
    """Base dialect inspector — no-op defaults suitable for generic/unknown dialects."""

    def get_enums(self, engine: Engine) -> list[SchemaEnum]:
        return []

    def filter_indexes(self, indexes: list[Any]) -> list[Any]:
        return indexes

    def extract_column_enums(
        self, col_type: TypeEngine, col_name: str
    ) -> dict[str, list[str]]:
        """Extract named enum types from a SQLAlchemy column type, if the dialect supports them."""
        return {}
