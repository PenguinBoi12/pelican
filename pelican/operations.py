from abc import ABC, abstractmethod
from dataclasses import dataclass
from contextlib import contextmanager
from typing import TypeVar, Any, Iterator
from sqlalchemy.types import TypeEngine
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import func
from sqlalchemy import (
    Table,
    Column,
    Integer,
    Float,
    Double,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    MetaData,
)
from .compilers import DialectCompiler

_T = TypeVar("_T", bound=Any)


# TODO: Move to compiler?
@dataclass
class Operation(ABC):
    table_name: str

    def execute(self, compiler: DialectCompiler, connection) -> None:
        """Execute this operation using the dialect adapter"""
        ddl = self.to_ddl(compiler)
        compiler.execute_ddl(connection, ddl)

    @abstractmethod
    def to_ddl(self, compiler: DialectCompiler) -> DDLElement | list[DDLElement]:
        """Convert operation to SQL for specific dialect"""
        pass


@dataclass
class AddColumn(Operation):
    column: Column

    def to_ddl(self, compiler: DialectCompiler) -> DDLElement:
        return compiler.add_column(self.table_name, self.column)


@dataclass
class DropColumn(Operation):
    column_name: str

    def to_ddl(self, compiler: DialectCompiler) -> DDLElement:
        return compiler.drop_column(self.table_name, self.column_name)


@dataclass
class RenameColumn(Operation):
    old_name: str
    new_name: str

    def to_ddl(self, compiler: DialectCompiler) -> DDLElement:
        return compiler.rename_column(self.table_name, self.old_name, self.new_name)


@dataclass
class AlterColumn(Operation):
    column_name: str
    new_type: TypeEngine | None = None
    nullable: bool | None = None
    default: Any = None
    server_default: Any = None

    def to_ddl(self, compiler: DialectCompiler) -> DDLElement | list[DDLElement]:
        return compiler.alter_column(
            self.table_name,
            self.column_name,
            new_type=self.new_type,
            nullable=self.nullable,
            default=self.default,
            server_default=self.server_default,
        )


@dataclass
class CreateIndex(Operation):
    index_name: str
    column_names: list[str]
    unique: bool

    def to_ddl(self, compiler: DialectCompiler) -> DDLElement:
        return compiler.create_index(
            self.table_name, self.index_name, self.column_names, self.unique
        )


@dataclass
class RemoveIndex(Operation):
    index_name: str

    def to_ddl(self, compiler: DialectCompiler) -> DDLElement:
        return compiler.drop_index(self.table_name, self.index_name)


class TableBuilder:
    def __init__(
        self,
        table_name: str,
        metadata: MetaData,
        primary_key: bool = True,
        table: Table | None = None,
    ) -> None:
        self.table_name = table_name
        self.metadata = metadata
        self.table = table if table is not None else Table(self.table_name, metadata)

        self._is_existing_table = table is not None
        self.operations: list[Operation] = []

        if primary_key and not self._is_existing_table:
            self.integer("id", primary_key=True, autoincrement=True)

    def column(self, name: str, type_: _T, *args: Any, **kwargs: Any) -> None:
        column_ = Column(name, type_, *args, **kwargs)
        self.table.append_column(column_, replace_existing=True)

        if self._is_existing_table:
            self.operations.append(AddColumn(self.table_name, column_))

    def alter(self, name: str, **kwargs: Any) -> None:
        if not self._is_existing_table:
            raise ValueError("remove_column can only be used on existing table")
        raise NotImplementedError()

    def rename(self, old_name: str, new_name: str) -> None:
        if not self._is_existing_table:
            raise ValueError("remove_column can only be used on existing table")
        self.operations.append(RenameColumn(self.table_name, old_name, new_name))

    def drop(self, name: str) -> None:
        if not self._is_existing_table:
            raise ValueError("remove_column can only be used on existing table")
        self.operations.append(DropColumn(self.table_name, name))

    def integer(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.column(name, Integer, *args, **kwargs)

    def float(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.column(name, Float, *args, **kwargs)

    def double(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.column(name, Double, *args, **kwargs)

    def boolean(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.column(name, Boolean, *args, **kwargs)

    def string(self, name: str, length: int = 255, *args: Any, **kwargs: Any) -> None:
        self.column(name, String(length), *args, **kwargs)

    def text(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.column(name, Text, *args, **kwargs)

    def datetime(self, name: str, *args: Any, **kwargs: Any) -> None:
        default = kwargs.pop("default", func.now())
        self.column(name, DateTime, default=default, *args, **kwargs)

    def timestamps(self) -> None:
        self.datetime("created_at", nullable=False)
        self.datetime("updated_at", onupdate=func.now(), nullable=False)

    def references(
        self, table_name: str, on_delete: str = "CASCADE", **kwargs: Any
    ) -> None:
        self.table.append_column(
            Column(
                f"{table_name.rstrip('s')}_id",
                Integer,
                ForeignKey(f"{table_name}.id", ondelete=on_delete),
                **kwargs,
            )
        )

    def index(
        self, column_names: list[str], *, name: str | None = None, unique: bool = False
    ) -> None:
        if not column_names:
            raise ValueError("At least one column name is required for an index")

        if name is None:
            name = f"{self.table_name}_{'_'.join(column_names)}_idx"

        self.operations.append(
            CreateIndex(self.table_name, name, column_names, unique=unique)
        )

    def remove_index(
        self, column_names: list[str] | None = None, *, name: str | None = None
    ):
        if not self._is_existing_table:
            raise ValueError("remove_index can only be used on existing table")

        if not column_names and not name:
            raise ValueError("At least one column name is required for an index")

        if name is None:
            name = f"{self.table_name}_{'_'.join(column_names)}_idx"

        self.operations.append(RemoveIndex(self.table_name, name))


@contextmanager
def create_table(table_name: str, primary_key: bool = True) -> Iterator[TableBuilder]:
    """Create a new table

    ## Example

    ```python
    from pelican import create_table


    @migration.up()
    def upgrade():
        with create_table('spaceships') as t:
            t.string('name', nullable=False)
            t.string('designation', nullable=False)
            t.integer('crew_capacity', default=1)
            t.timestamps()
    ```
    """
    from pelican import runner

    builder = TableBuilder(table_name, runner.metadata, primary_key=primary_key)
    yield builder

    with runner.engine.begin() as conn:
        builder.table.create(conn, checkfirst=True)

        for operation in builder.operations:
            operation.execute(runner.compiler, conn)


@contextmanager
def change_table(table_name: str) -> Iterator[TableBuilder]:
    """Create a new table

    ## Example

    ```python
    from pelican import change_table


    @migration.up()
    def upgrade():
        with change_table('spaceships') as t:
            t.string('name', nullable=False) # add column
            t.alter('name', nullable=True) # alter column
            t.rename('name', 'new_name') # rename column
            t.drop('new_name') # drop column
    ```
    """
    from pelican import runner

    table = Table(
        table_name, runner.metadata, autoload_with=runner.engine, extend_existing=True
    )

    builder = TableBuilder(table_name, runner.metadata, table=table)
    yield builder

    with runner.engine.begin() as conn:
        for operation in builder.operations:
            try:
                operation.execute(runner.compiler, conn)
            except NotImplementedError as e:
                # Handle SQLite limitations gracefully
                if "SQLite" in str(e) and isinstance(operation, AlterColumnOperation):
                    raise NotImplementedError(
                        f"SQLite does not support altering column '{operation.column_name}'. "
                        f"Consider using batch_alter_table() or recreating the table manually."
                    ) from e
                raise


def drop_table(table_name: str) -> None:
    """Drop an existing table

    ## Example

    ```python
    from pelican import drop_table


    @migration.down()
    def downgrade():
        drop_table('spaceships')
    ```
    """
    from pelican import runner

    with runner.engine.begin() as conn:
        table = Table(table_name, runner.metadata, autoload_with=runner.engine)
        table.drop(conn)
