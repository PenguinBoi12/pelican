from typing import Any, Iterable
from sqlalchemy.types import TypeEngine
from sqlalchemy.schema import DDL
from sqlalchemy.schema import DDLElement
from .compiler import DialectCompiler


class SQLiteCompiler(DialectCompiler):
    def rename_column(
        self, table_name: str, old_name: str, new_name: str
    ) -> Iterable[DDLElement]:
        return [DDL(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}")]

    def alter_column(
        self,
        table_name: str,
        column_name: str,
        new_type: TypeEngine | None = None,
        nullable: bool | None = None,
        default: Any = None,
        server_default: Any = None,
    ) -> DDLElement:
        """SQLite doesn't support ALTER COLUMN"""
        raise NotImplementedError(
            f"SQLite does not support ALTER COLUMN for '{column_name}'. "
            "Column type/constraint changes require table recreation. "
            "Use batch_alter_table() instead."
        )
