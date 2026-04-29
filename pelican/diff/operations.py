from abc import ABC, abstractmethod
from dataclasses import dataclass

from .schema import (
    SchemaTable,
    SchemaColumn,
    SchemaIndex,
    SchemaCheckConstraint,
    SchemaForeignKey,
    SchemaEnum,
)


class DiffOperation(ABC):
    @abstractmethod
    def render_up(self) -> list[str]: ...

    @abstractmethod
    def render_down(self) -> list[str]: ...

    @abstractmethod
    def __str__(self) -> str: ...


def _extract_length(type_str: str) -> int | None:
    if "(" in type_str and ")" in type_str:
        try:
            return int(type_str[type_str.index("(") + 1 : type_str.index(")")])
        except ValueError:
            return None
    return None


def _type_to_method(type_str: str) -> str:
    base = type_str.split("(")[0].upper()
    return {
        "INTEGER": "integer",
        "BIGINT": "integer",
        "SMALLINT": "integer",
        "FLOAT": "float",
        "REAL": "float",
        "DOUBLE": "double",
        "VARCHAR": "string",
        "CHAR": "string",
        "TEXT": "text",
        "BOOLEAN": "boolean",
        "BOOL": "boolean",
        "DATETIME": "datetime",
        "TIMESTAMP": "datetime",
        "TIMESTAMPTZ": "datetime",
    }.get(base, "string")


def _type_to_call(type_str: str) -> str:
    base = type_str.split("(")[0].upper()
    length = _extract_length(type_str)
    if base in ("VARCHAR", "CHAR") and length:
        return f"String({length})"
    return {
        "INTEGER": "Integer()",
        "BIGINT": "BigInteger()",
        "SMALLINT": "SmallInteger()",
        "FLOAT": "Float()",
        "REAL": "Float()",
        "DOUBLE": "Double()",
        "TEXT": "Text()",
        "BOOLEAN": "Boolean()",
        "DATETIME": "DateTime()",
        "TIMESTAMP": "DateTime()",
        "TIMESTAMPTZ": "DateTime(timezone=True)",
    }.get(base, f"Text()  # {type_str}")


def render_column_call(col: SchemaColumn) -> str:
    method = _type_to_method(col.type)
    args: list[str] = [repr(col.name)]
    length = _extract_length(col.type)
    if length and method == "string":
        args.append(str(length))
    if not col.nullable:
        args.append("nullable=False")
    if col.server_default is not None:
        args.append(f"server_default=text({col.server_default!r})")
    return f"t.{method}({', '.join(args)})"


def _render_table_block(table: SchemaTable) -> list[str]:
    lines = [f"with create_table({table.name!r}) as t:"]
    for col in table.columns:
        if col.primary_key:
            continue
        lines.append(f"    {render_column_call(col)}")
    for idx in table.indexes:
        unique_part = ", unique=True" if idx.unique else ""
        lines.append(f"    t.index({idx.columns!r}, name={idx.name!r}{unique_part})")
    return lines


@dataclass
class CreateTable(DiffOperation):
    table: SchemaTable

    def __str__(self) -> str:
        return f"+ Create table: {self.table.name}"

    def render_up(self) -> list[str]:
        return _render_table_block(self.table)

    def render_down(self) -> list[str]:
        return [f"drop_table({self.table.name!r})"]


@dataclass
class DropTable(DiffOperation):
    table: SchemaTable

    def __str__(self) -> str:
        return f"- Drop table: {self.table.name}"

    def render_up(self) -> list[str]:
        return [f"drop_table({self.table.name!r})"]

    def render_down(self) -> list[str]:
        return _render_table_block(self.table)


@dataclass
class AddColumn(DiffOperation):
    table_name: str
    column: SchemaColumn

    def __str__(self) -> str:
        return f"~ {self.table_name}: add column {self.column.name} {self.column.type}"

    def render_up(self) -> list[str]:
        return [render_column_call(self.column)]

    def render_down(self) -> list[str]:
        return [f"t.drop({self.column.name!r})"]


@dataclass
class DropColumn(DiffOperation):
    table_name: str
    column: SchemaColumn

    def __str__(self) -> str:
        return f"~ {self.table_name}: drop column {self.column.name}"

    def render_up(self) -> list[str]:
        return [f"t.drop({self.column.name!r})"]

    def render_down(self) -> list[str]:
        return [render_column_call(self.column)]


@dataclass
class RenameColumn(DiffOperation):
    table_name: str
    old_name: str
    new_name: str
    confidence: float
    old_col: "SchemaColumn"
    new_col: "SchemaColumn"

    def __str__(self) -> str:
        pct = int(self.confidence * 100)
        return f"~ {self.table_name}: rename column {self.old_name} → {self.new_name} [{pct}% confidence]"

    def to_drop_add(self) -> "tuple[DropColumn, AddColumn]":
        return DropColumn(self.table_name, self.old_col), AddColumn(
            self.table_name, self.new_col
        )

    def render_up(self) -> list[str]:
        return [f"t.rename({self.old_name!r}, {self.new_name!r})"]

    def render_down(self) -> list[str]:
        return [f"t.rename({self.new_name!r}, {self.old_name!r})"]


@dataclass
class AlterColumnType(DiffOperation):
    table_name: str
    column_name: str
    old_type: str
    new_type: str

    def __str__(self) -> str:
        return f"~ {self.table_name}: alter {self.column_name} type {self.old_type} → {self.new_type}"

    def render_up(self) -> list[str]:
        return [
            f"t.alter({self.column_name!r}, new_type={_type_to_call(self.new_type)})"
        ]

    def render_down(self) -> list[str]:
        return [
            f"t.alter({self.column_name!r}, new_type={_type_to_call(self.old_type)})"
        ]


@dataclass
class AlterColumnNullable(DiffOperation):
    table_name: str
    column_name: str
    old_nullable: bool
    new_nullable: bool

    def __str__(self) -> str:
        return f"~ {self.table_name}: alter {self.column_name} nullable {self.old_nullable} → {self.new_nullable}"

    def render_up(self) -> list[str]:
        return [f"t.alter({self.column_name!r}, nullable={self.new_nullable!r})"]

    def render_down(self) -> list[str]:
        return [f"t.alter({self.column_name!r}, nullable={self.old_nullable!r})"]


@dataclass
class AlterColumnServerDefault(DiffOperation):
    table_name: str
    column_name: str
    old_server_default: str | None
    new_server_default: str | None

    def __str__(self) -> str:
        return f"~ {self.table_name}: alter {self.column_name} server_default {self.old_server_default!r} → {self.new_server_default!r}"

    def render_up(self) -> list[str]:
        val = (
            f"text({self.new_server_default!r})"
            if self.new_server_default is not None
            else "None"
        )
        return [f"t.alter({self.column_name!r}, server_default={val})"]

    def render_down(self) -> list[str]:
        val = (
            f"text({self.old_server_default!r})"
            if self.old_server_default is not None
            else "None"
        )
        return [f"t.alter({self.column_name!r}, server_default={val})"]


@dataclass
class CreateIndex(DiffOperation):
    table_name: str
    index: SchemaIndex

    def __str__(self) -> str:
        return f"~ {self.table_name}: add index {self.index.name}"

    def render_up(self) -> list[str]:
        unique_part = ", unique=True" if self.index.unique else ""
        return [
            f"t.index({self.index.columns!r}, name={self.index.name!r}{unique_part})"
        ]

    def render_down(self) -> list[str]:
        return [f"t.remove_index(name={self.index.name!r})"]


@dataclass
class DropIndex(DiffOperation):
    table_name: str
    index: SchemaIndex

    def __str__(self) -> str:
        return f"~ {self.table_name}: drop index {self.index.name}"

    def render_up(self) -> list[str]:
        return [f"t.remove_index(name={self.index.name!r})"]

    def render_down(self) -> list[str]:
        unique_part = ", unique=True" if self.index.unique else ""
        return [
            f"t.index({self.index.columns!r}, name={self.index.name!r}{unique_part})"
        ]


@dataclass
class AddCheckConstraint(DiffOperation):
    table_name: str
    constraint: SchemaCheckConstraint

    def __str__(self) -> str:
        return f"~ {self.table_name}: add check constraint {self.constraint.name}"

    def render_up(self) -> list[str]:
        return [
            f"# TODO: add check constraint {self.constraint.name!r}: {self.constraint.expression}"
        ]

    def render_down(self) -> list[str]:
        return [f"# TODO: drop check constraint {self.constraint.name!r}"]


@dataclass
class DropCheckConstraint(DiffOperation):
    table_name: str
    constraint: SchemaCheckConstraint

    def __str__(self) -> str:
        return f"~ {self.table_name}: drop check constraint {self.constraint.name}"

    def render_up(self) -> list[str]:
        return [f"# TODO: drop check constraint {self.constraint.name!r}"]

    def render_down(self) -> list[str]:
        return [
            f"# TODO: re-add check constraint {self.constraint.name!r}: {self.constraint.expression}"
        ]


@dataclass
class CreateEnum(DiffOperation):
    enum: SchemaEnum

    def __str__(self) -> str:
        return f"+ Create enum: {self.enum.name}"

    def render_up(self) -> list[str]:
        return [
            f"# TODO: CREATE TYPE {self.enum.name} AS ENUM {tuple(self.enum.values)!r}"
        ]

    def render_down(self) -> list[str]:
        return [f"# TODO: DROP TYPE {self.enum.name}"]


@dataclass
class DropEnum(DiffOperation):
    enum: SchemaEnum

    def __str__(self) -> str:
        return f"- Drop enum: {self.enum.name}"

    def render_up(self) -> list[str]:
        return [f"# TODO: DROP TYPE {self.enum.name}"]

    def render_down(self) -> list[str]:
        return [
            f"# TODO: CREATE TYPE {self.enum.name} AS ENUM {tuple(self.enum.values)!r}"
        ]


@dataclass
class AddEnumValue(DiffOperation):
    enum_name: str
    value: str

    def __str__(self) -> str:
        return f"~ enum {self.enum_name}: add value {self.value!r}"

    def render_up(self) -> list[str]:
        return [
            f"# ALTER TYPE {self.enum_name} ADD VALUE {self.value!r}  # Postgres: safe append"
        ]

    def render_down(self) -> list[str]:
        return [
            f"# WARNING: removing enum value {self.value!r} from {self.enum_name} in rollback requires a table rewrite."
        ]


@dataclass
class RemoveEnumValue(DiffOperation):
    enum_name: str
    value: str

    def __str__(self) -> str:
        return f"~ enum {self.enum_name}: remove value {self.value!r} [WARNING: requires table rewrite]"

    def render_up(self) -> list[str]:
        return [
            f"# WARNING: removing enum value {self.value!r} from {self.enum_name} requires a table rewrite. Implement manually."
        ]

    def render_down(self) -> list[str]:
        return [
            f"# WARNING: re-adding enum value {self.value!r} to {self.enum_name} — check ordering."
        ]


@dataclass
class AddForeignKey(DiffOperation):
    table_name: str
    fk: SchemaForeignKey

    def __str__(self) -> str:
        return f"~ {self.table_name}: add foreign key {self.fk.columns!r} → {self.fk.ref_table}"

    def render_up(self) -> list[str]:
        on_delete = f" ON DELETE {self.fk.on_delete}" if self.fk.on_delete else ""
        return [
            f"# TODO: ADD CONSTRAINT {self.fk.name!r} FOREIGN KEY {self.fk.columns!r} REFERENCES {self.fk.ref_table!r} {self.fk.ref_columns!r}{on_delete}"
        ]

    def render_down(self) -> list[str]:
        return [f"# TODO: DROP CONSTRAINT {self.fk.name!r}"]


@dataclass
class DropForeignKey(DiffOperation):
    table_name: str
    fk: SchemaForeignKey

    def __str__(self) -> str:
        return f"~ {self.table_name}: drop foreign key {self.fk.columns!r} → {self.fk.ref_table}"

    def render_up(self) -> list[str]:
        return [f"# TODO: DROP CONSTRAINT {self.fk.name!r}"]

    def render_down(self) -> list[str]:
        on_delete = f" ON DELETE {self.fk.on_delete}" if self.fk.on_delete else ""
        return [
            f"# TODO: ADD CONSTRAINT {self.fk.name!r} FOREIGN KEY {self.fk.columns!r} REFERENCES {self.fk.ref_table!r} {self.fk.ref_columns!r}{on_delete}"
        ]
