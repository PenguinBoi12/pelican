from typing import Any, Iterable
from sqlalchemy.types import TypeEngine
from sqlalchemy.schema import DDL
from .compiler import DialectCompiler
from pelican._types import UnsupportedDialectError


class SQLiteCompiler(DialectCompiler):
    def rename_column(
        self, table_name: str, old_name: str, new_name: str
    ) -> Iterable[DDL]:
        return [DDL(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}")]

    def alter_column(
        self,
        table_name: str,
        column_name: str,
        new_type: TypeEngine | None = None,
        nullable: bool | None = None,
        default: Any = None,
        server_default: Any = None,
    ) -> Iterable[DDL]:
        raise UnsupportedDialectError(
            f"SQLite does not support ALTER COLUMN for '{column_name}'. "
            "Column type/constraint changes require table recreation."
        )

    def add_foreign_key(
        self,
        table_name: str,
        columns: list[str],
        ref_table: str,
        ref_columns: list[str],
        name: str | None = None,
        on_delete: str | None = None,
    ) -> Iterable[DDL]:
        raise UnsupportedDialectError(
            f"SQLite does not support ADD CONSTRAINT FOREIGN KEY on '{table_name}'. "
            "Foreign key changes require table recreation."
        )

    def drop_foreign_key(self, table_name: str, constraint_name: str) -> Iterable[DDL]:
        raise UnsupportedDialectError(
            f"SQLite does not support DROP CONSTRAINT on '{table_name}'. "
            "Foreign key changes require table recreation."
        )
