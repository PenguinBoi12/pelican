from sqlalchemy import MetaData
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.schema import CheckConstraint, ForeignKeyConstraint

from .dialects import inspector_for
from .schema import (
    SchemaState,
    SchemaTable,
    SchemaColumn,
    SchemaIndex,
    SchemaCheckConstraint,
    SchemaForeignKey,
    SchemaEnum,
)
from .normalizer import (
    normalize_type,
    normalize_server_default,
    normalize_check_expression,
)

_EXCLUDED_TABLES = {"pelican_migration"}


def extract_from_metadata(metadata: MetaData, dialect: Dialect) -> SchemaState:
    dialect_name = dialect.name
    dialect_inspector = inspector_for(dialect_name)
    enums: dict[str, list[str]] = {}
    tables = []

    for table in sorted(metadata.sorted_tables, key=lambda t: t.name):
        if table.name in _EXCLUDED_TABLES:
            continue
        schema_table, table_enums = _extract_table(table, dialect, dialect_inspector)
        tables.append(schema_table)
        enums.update(table_enums)

    schema_enums = [SchemaEnum(name=n, values=v) for n, v in sorted(enums.items())]
    return SchemaState(dialect=dialect_name, tables=tables, enums=schema_enums)


def _extract_table(
    table, dialect: Dialect, dialect_inspector
) -> tuple[SchemaTable, dict[str, list[str]]]:
    enums: dict[str, list[str]] = {}
    pk_cols = {col.name for col in table.primary_key.columns}

    columns = []
    for position, col in enumerate(table.columns):
        col_type = col.type
        type_str = normalize_type(str(col_type.compile(dialect=dialect)))

        enums.update(dialect_inspector.extract_column_enums(col_type, col.name))

        server_default = _extract_server_default(col)

        columns.append(
            SchemaColumn(
                name=col.name,
                type=type_str,
                nullable=col.nullable if col.nullable is not None else True,
                primary_key=col.name in pk_cols,
                autoincrement=bool(getattr(col, "autoincrement", False)),
                server_default=(
                    normalize_server_default(server_default) if server_default else None
                ),
                position=position,
            )
        )

    indexes = [
        SchemaIndex(
            name=idx.name,
            columns=[col.name for col in idx.columns],
            unique=bool(idx.unique),
        )
        for idx in table.indexes
        if idx.name
    ]

    check_constraints = []
    foreign_keys = []

    for constraint in table.constraints:
        if isinstance(constraint, CheckConstraint):
            expr = str(constraint.sqltext)
            check_constraints.append(
                SchemaCheckConstraint(
                    name=constraint.name,
                    expression=normalize_check_expression(expr),
                )
            )
        elif isinstance(constraint, ForeignKeyConstraint):
            if constraint.elements:
                ref_table = constraint.elements[0].column.table.name
                ref_columns = [fk.column.name for fk in constraint.elements]
                on_delete = constraint.ondelete
                foreign_keys.append(
                    SchemaForeignKey(
                        name=constraint.name,
                        columns=[col.name for col in constraint.columns],
                        ref_table=ref_table,
                        ref_columns=ref_columns,
                        on_delete=on_delete,
                    )
                )

    return (
        SchemaTable(
            name=table.name,
            columns=columns,
            indexes=indexes,
            check_constraints=check_constraints,
            foreign_keys=foreign_keys,
        ),
        enums,
    )


def _extract_server_default(col) -> str | None:
    sd = col.server_default
    if sd is None:
        return None
    # text('...') server defaults
    if hasattr(sd, "arg"):
        arg = sd.arg
        if hasattr(arg, "text"):
            return arg.text
        return str(arg)
    # FetchedValue (DB-controlled, no expression available)
    return None
