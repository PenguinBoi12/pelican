from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.sqltypes import Enum as SAEnum
from sqlalchemy.types import TypeEngine

from .base import DialectInspector
from ..schema import SchemaEnum


class PostgreSQLInspector(DialectInspector):
    def get_enums(self, engine: Engine) -> list[SchemaEnum]:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                    SELECT t.typname AS name, e.enumlabel AS value
                    FROM pg_type t
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public'
                    ORDER BY t.typname, e.enumsortorder
                    """)).fetchall()

        enums: dict[str, list[str]] = {}
        for name, value in rows:
            enums.setdefault(name, []).append(value)

        return [SchemaEnum(name=name, values=values) for name, values in enums.items()]

    def extract_column_enums(
        self, col_type: TypeEngine, col_name: str
    ) -> dict[str, list[str]]:
        if isinstance(col_type, SAEnum) and col_type.name:
            return {col_type.name: list(col_type.enums)}
        return {}
