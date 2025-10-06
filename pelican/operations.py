from contextlib import contextmanager
from typing import TypeVar, Any, Iterator
from sqlalchemy.sql import func
from sqlalchemy import (
    Table,
    Column,
    Index,
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
from sqlalchemy.schema import CreateColumn, DDL

_T = TypeVar("_T", bound=Any)


class TableBuilder:
    def __init__(
        self,
        table_name: str,
        metadata: MetaData,
        primary_key: bool = True,
        table: Table | None = None
    ) -> None:
        self.table_name = table_name
        self.metadata = metadata
        self.table = table

        self._is_existing_table = table is not None
        self.columns_to_add: list[Column] = []
        self.columns_to_remove: list[str] = []

        if self.table is None:
            self.table = Table(self.table_name, metadata)

        if primary_key and not self._is_existing_table:
            self.integer("id", primary_key=True, autoincrement=True)


    def add_column(self, name: str, type_: _T, *args, **kwargs) -> None:
        column = Column(name, type_, *args, **kwargs)

        if self._is_existing_table:
            self.columns_to_add.append(column)

        self.table.append_column(column, replace_existing=True)

    # rename_column
    # change_column

    def remove_column(self, name: str) -> None:
        if not self.table:
            raise ValueError("remove_column can only be used on existing table")
        self._columns_to_remove.append(name)

    # change
    # remove

    def integer(self, name: str, *args, **kwargs) -> None:
        self.add_column(name, Integer, *args, **kwargs)

    def float(self, name: str, *args, **kwargs) -> None:
        self.add_column(name, Float, *args, **kwargs)

    def double(self, name: str, *args, **kwargs) -> None:
        self.add_column(name, Double, *args, **kwargs)

    def boolean(self, name: str, *args, **kwargs) -> None:
        self.add_column(name, Boolean, *args, **kwargs)

    def string(self, name: str, length: int = 255, *args, **kwargs) -> None:
        self.add_column(name, String(length), *args, **kwargs)

    def text(self, name: str, *args, **kwargs) -> None:
        self.add_column(name, Text, *args, **kwargs)

    def datetime(self, name: str, *args, **kwargs) -> None:
        default = kwargs.pop("default", func.now())
        self.add_column(name, DateTime, default=default, *args, **kwargs)

    def timestamps(self) -> None:
        self.datetime("created_at", nullable=False)
        self.datetime("updated_at", onupdate=func.now(), nullable=False)

    def references(self, table_name: str, on_delete: str = "CASCADE", **kwargs) -> None:
        self.table.append_column(
            Column(
                f"{table_name.rstrip('s')}_id",
                Integer,
                ForeignKey(f"{table_name}.id", ondelete=on_delete),
                **kwargs,
            )
        )

    def index(self, column_names: list[str], name: str | None = None, unique: bool = False) -> None:
        if not column_names:
            raise ValueError("At least one column name is required for an index")

        if name is None:
            suffix = "unique" if unique else "idx"
            name = f"{self.table_name}_{'_'.join(column_names)}_{suffix}"

        Index(name, *[self.table.c[col] for col in column_names], unique=unique)


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


@contextmanager
def  change_table(table_name: str) -> Iterator[TableBuilder]:
    from pelican import runner

    table = Table(
        table_name,
        runner.metadata,
        autoload_with=runner.engine,
        extend_existing=True
    )

    builder = TableBuilder(table_name, runner.metadata, table=table)
    yield builder

    with runner.engine.begin() as conn:
        for col in builder.columns_to_add:
            col_sql = str(CreateColumn(col).compile(dialect=runner.engine.dialect))
            ddl = DDL(f"ALTER TABLE {builder.table_name} ADD COLUMN {col_sql}")
            conn.execute(ddl)

        for name in builder.columns_to_remove:
            ddl = DDL(f"ALTER TABLE {builder.table_name} DROP COLUMN {name}")
            conn.execute(ddl)


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
