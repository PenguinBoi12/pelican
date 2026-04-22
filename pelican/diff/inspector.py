from sqlalchemy import inspect
from sqlalchemy.engine import Engine, Inspector

from .dialects import inspector_for
from .dialects.base import DialectInspector
from .schema import (
    SchemaState,
    SchemaTable,
    SchemaColumn,
    SchemaIndex,
    SchemaCheckConstraint,
    SchemaForeignKey,
)
from .normalizer import (
    normalize_type,
    normalize_server_default,
    normalize_check_expression,
)

_EXCLUDED_TABLES = {"pelican_migration"}


def introspect_live_db(engine: Engine) -> SchemaState:
    sa_inspector = inspect(engine)
    dialect_name = engine.dialect.name
    dialect = inspector_for(dialect_name)

    enums = dialect.get_enums(engine)
    tables = []

    for table_name in sorted(sa_inspector.get_table_names()):
        if table_name in _EXCLUDED_TABLES:
            continue
        tables.append(_inspect_table(sa_inspector, dialect, table_name))

    return SchemaState(dialect=dialect_name, tables=tables, enums=enums)


def _inspect_table(
    inspector: Inspector, dialect: DialectInspector, table_name: str
) -> SchemaTable:
    pk_cols = set(
        inspector.get_pk_constraint(table_name).get("constrained_columns", [])
    )

    columns = []
    for position, col in enumerate(inspector.get_columns(table_name)):
        raw_type = str(col["type"])
        server_default = col.get("default")

        columns.append(
            SchemaColumn(
                name=col["name"],
                type=normalize_type(raw_type),
                nullable=col["nullable"],
                primary_key=col["name"] in pk_cols,
                autoincrement=bool(col.get("autoincrement", False)),
                server_default=(
                    normalize_server_default(server_default) if server_default else None
                ),
                position=position,
            )
        )

    raw_indexes = dialect.filter_indexes(inspector.get_indexes(table_name))
    indexes = [
        SchemaIndex(
            name=idx["name"],
            columns=list(idx["column_names"]),
            unique=bool(idx["unique"]),
        )
        for idx in raw_indexes
        if idx.get("name")
    ]

    check_constraints = [
        SchemaCheckConstraint(
            name=cc.get("name"),
            expression=normalize_check_expression(cc["sqltext"]),
        )
        for cc in inspector.get_check_constraints(table_name)
    ]

    foreign_keys = [
        SchemaForeignKey(
            name=fk.get("name"),
            columns=list(fk["constrained_columns"]),
            ref_table=fk["referred_table"],
            ref_columns=list(fk["referred_columns"]),
            on_delete=fk.get("options", {}).get("ondelete"),
        )
        for fk in inspector.get_foreign_keys(table_name)
    ]

    return SchemaTable(
        name=table_name,
        columns=columns,
        indexes=indexes,
        check_constraints=check_constraints,
        foreign_keys=foreign_keys,
    )
