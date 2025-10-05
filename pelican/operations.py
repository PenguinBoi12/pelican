from contextlib import contextmanager
from typing import TypeVar, Any, Self, Iterator
from sqlalchemy.sql import func
from sqlalchemy.engine import Engine
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Index,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
)

_T = TypeVar("_T", bound=Any)


class TableBuilder:
    def __init__(
        self,
        table_name: str,
        metadata: MetaData,
        engine: Engine,
        primary_key: bool = True,
    ) -> None:
        self.table_name = table_name
        self.metadata = metadata
        self.engine = engine
        self.columns: list[Column[Any]] = []
        self.indexes: list[Index] = []

        if primary_key:
            self.integer("id", primary_key=True, autoincrement=True)

    def column(self, name: str, type_: _T, *args, **kwargs) -> Self:
        self.columns.append(Column(name, type_, *args, **kwargs))
        return self

    def integer(self, name: str, *args, **kwargs) -> Self:
        self.column(name, Integer, *args, **kwargs)
        return self

    def boolean(self, name: str, *args, **kwargs) -> Self:
        self.column(name, Boolean, *args, **kwargs)
        return self

    def string(self, name: str, length: int = 255, *args, **kwargs) -> Self:
        self.column(name, String(length), *args, **kwargs)
        return self

    def text(self, name: str, *args, **kwargs) -> Self:
        self.column(name, Text, *args, **kwargs)
        return self

    def datetime(self, name: str, *args, **kwargs) -> Self:
        default = kwargs.pop("default", func.now())
        self.column(name, DateTime, default=default, *args, **kwargs)
        return self

    def timestamps(self) -> Self:
        self.datetime("created_at", nullable=False)
        self.datetime("updated_at", onupdate=func.now(), nullable=False)
        return self

    # can be improved
    def references(self, table_name: str, on_delete: str = "CASCADE", **kwargs) -> Self:
        self.columns.append(
            Column(
                f"{table_name.rstrip('s')}_id",
                Integer,
                ForeignKey(f"{table_name}.id", ondelete=on_delete),
                **kwargs,
            )
        )
        return self

    def build(self) -> Table:
        """Build and create the table in the database."""
        table = Table(self.table_name, self.metadata, *self.columns)
        table.create(self.engine, checkfirst=True)

        for index_info in self.indexes:
            idx = Index(
                index_info["name"],
                *[table.c[col] for col in index_info["columns"]],
                unique=index_info["unique"],
            )
            idx.create(self.engine)
        return table


@contextmanager
def create_table(table_name: str) -> Iterator[TableBuilder]:
    from pelican import runner

    builder = TableBuilder(table_name, runner.metadata, runner.engine)
    yield builder
    builder.build()


def drop_table(table_name: str) -> None:
    from pelican import runner

    Table(table_name, runner.metadata, autoload_with=runner.engine).drop(runner.engine)
