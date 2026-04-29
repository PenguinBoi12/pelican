from abc import ABC, abstractmethod
from typing import Any, Iterable
from sqlalchemy.types import TypeEngine
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Executable, DDLElement
from sqlalchemy.schema import (
    CreateColumn,
    CreateIndex,
    DDL,
    DropIndex,
)
from sqlalchemy import (
    text,
    Table,
    Column,
    Index,
    Double,
    MetaData,
)


class DialectCompiler(ABC):
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.dialect = engine.dialect

    def add_column(self, table_name: str, column: Column) -> Iterable[Executable]:
        sql = f"ALTER TABLE {table_name} ADD COLUMN {CreateColumn(column).compile(dialect=self.dialect)}"
        return [text(sql)]

    def drop_column(self, table_name: str, column_name: str) -> Iterable[Executable]:
        sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
        return [text(sql)]

    @abstractmethod
    def rename_column(
        self, table_name: str, old_name: str, new_name: str
    ) -> Iterable[DDL]:
        pass

    @abstractmethod
    def alter_column(
        self,
        table_name: str,
        column_name: str,
        new_type: TypeEngine | None = None,
        nullable: bool | None = None,
        default: Any = None,
        server_default: Any = None,
    ) -> Iterable[DDL]:
        pass

    def create_index(
        self,
        table_name: str,
        index_name: str,
        column_names: list[str],
        unique: bool = False,
    ) -> Iterable[DDLElement]:
        metadata = MetaData()
        table = Table(
            table_name, metadata, autoload_with=self.engine, extend_existing=True
        )

        columns = [table.c[col_name] for col_name in column_names]
        index = Index(index_name, *columns, unique=unique)

        return [CreateIndex(index)]

    def drop_index(self, table_name: str, index_name: str) -> Iterable[DDLElement]:
        metadata = MetaData()
        table = Table(table_name, metadata)
        index = Index(index_name, _table=table)

        return [DropIndex(index)]

    def add_foreign_key(
        self,
        table_name: str,
        columns: list[str],
        ref_table: str,
        ref_columns: list[str],
        name: str | None = None,
        on_delete: str | None = None,
    ) -> Iterable[DDL]:
        cols = ", ".join(columns)
        ref_cols = ", ".join(ref_columns)
        constraint = f"CONSTRAINT {name} " if name else ""
        on_delete_clause = f" ON DELETE {on_delete}" if on_delete else ""
        return [
            DDL(
                f"ALTER TABLE {table_name} ADD {constraint}"
                f"FOREIGN KEY ({cols}) REFERENCES {ref_table} ({ref_cols}){on_delete_clause}"
            )
        ]

    def drop_foreign_key(self, table_name: str, constraint_name: str) -> Iterable[DDL]:
        return [DDL(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")]
