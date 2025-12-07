from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.types import TypeEngine
from sqlalchemy.schema import (
    DDL,
    CreateColumn,
    CreateIndex,
    DropIndex,
    DDLElement,
)
from sqlalchemy import (
    Table,
    Column,
    Index,
    Double,
    MetaData,
)


class DialectCompiler(ABC):
    def __init__(self, engine):
        self.engine = engine
        self.dialect = engine.dialect

    def add_column(self, table_name: str, column: Column) -> DDLElement:
        col_expr = CreateColumn(column).compile(dialect=self.dialect)
        return DDL(f"ALTER TABLE {table_name} ADD COLUMN {str(col_expr)}")

    def drop_column(self, table_name: str, column_name: str) -> DDLElement:
        return DDL(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")

    @abstractmethod
    def rename_column(self, table_name: str, old_name: str, new_name: str) -> DDLElement:
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
    ) -> DDLElement | list[DDLElement]:
        pass

    def create_index(
        self,
        table_name: str,
        index_name: str,
        column_names: list[str],
        unique: bool = False,
    ) -> DDLElement:
        metadata = MetaData()
        table = Table(
            table_name,
            metadata,
            autoload_with=self.engine,
            extend_existing=True
        )

        columns = [table.c[col_name] for col_name in column_names]
        index = Index(index_name, *columns, unique=unique)

        return CreateIndex(index)

    def drop_index(self, table_name: str, index_name: str) -> DDLElement:
        metadata = MetaData()
        table = Table(table_name, metadata)
        index = Index(index_name, _table=table)

        return DropIndex(index)

    def execute_ddl(self, connection, ddl: DDLElement | list[DDLElement]) -> None:
        def execute(s):
            sql = str(ddl.compile(dialect=self.dialect))
            connection.exec_driver_sql(sql)

        if isinstance(ddl, list):
            for statement in ddl:
                execute(statement)
        else:
            execute(ddl)
