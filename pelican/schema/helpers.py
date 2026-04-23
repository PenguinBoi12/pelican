from typing import TypeVar, Any, Iterator
from contextlib import contextmanager
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
import inflection

from pelican._context import get_runner
from pelican.schema.operations import (
    Operation,
    AddColumn,
    DropColumn,
    RenameColumn,
    AlterColumn,
    CreateIndex,
    RemoveIndex,
)

_T = TypeVar("_T", bound=Any)


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
        # TODO: Add Column class for the builder which would then be used to build the SA Column in the compiler
        self.table.append_column(column_, replace_existing=True)

        if self._is_existing_table:
            self.operations.append(AddColumn(self.table_name, column_))

    def alter(self, name: str, **kwargs: Any) -> None:
        if not self._is_existing_table:
            raise ValueError("alter can only be used on existing table")
        self.operations.append(AlterColumn(self.table_name, name, **kwargs))

    def rename(self, old_name: str, new_name: str) -> None:
        if not self._is_existing_table:
            raise ValueError("rename can only be used on existing table")
        self.operations.append(RenameColumn(self.table_name, old_name, new_name))

    def drop(self, name: str) -> None:
        if not self._is_existing_table:
            raise ValueError("drop can only be used on existing table")
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
        self, model_name: str, on_delete: str = "CASCADE", **kwargs: Any
    ) -> None:
        self.table.append_column(
            Column(
                f"{model_name}_id",
                Integer,
                ForeignKey(
                    f"{inflection.pluralize(model_name)}.id", ondelete=on_delete
                ),
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
    ) -> None:
        if not self._is_existing_table:
            raise ValueError("remove_index can only be used on existing table")

        if not name:
            if not column_names:
                raise ValueError("At least one column name is required for an index")
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
    runner = get_runner()
    builder = TableBuilder(table_name, runner.metadata, primary_key=primary_key)
    yield builder

    with runner.engine.connect() as conn:
        with conn.begin():
            builder.table.create(conn, checkfirst=True)

    runner.execute_operations(builder.operations)


@contextmanager
def change_table(table_name: str) -> Iterator[TableBuilder]:
    """Modify an existing table

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
    runner = get_runner()
    table = Table(
        table_name, runner.metadata, autoload_with=runner.engine, extend_existing=True
    )

    builder = TableBuilder(table_name, runner.metadata, table=table)
    yield builder

    runner.execute_operations(builder.operations)


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
    runner = get_runner()

    with runner.engine.connect() as conn:
        with conn.begin():
            table = Table(table_name, runner.metadata, autoload_with=runner.engine)
            table.drop(conn)
