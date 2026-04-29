from dataclasses import dataclass, field


@dataclass
class SchemaColumn:
    name: str
    type: str  # normalized canonical string
    nullable: bool
    primary_key: bool
    autoincrement: bool
    server_default: str | None
    position: int  # ordinal, used by rename heuristic


@dataclass
class SchemaIndex:
    name: str
    columns: list[str]
    unique: bool


@dataclass
class SchemaCheckConstraint:
    name: str | None
    expression: str  # normalized


@dataclass
class SchemaForeignKey:
    name: str | None
    columns: list[str]
    ref_table: str
    ref_columns: list[str]
    on_delete: str | None


@dataclass
class SchemaTable:
    name: str
    columns: list[SchemaColumn] = field(default_factory=list)
    indexes: list[SchemaIndex] = field(default_factory=list)
    check_constraints: list[SchemaCheckConstraint] = field(default_factory=list)
    foreign_keys: list[SchemaForeignKey] = field(default_factory=list)


@dataclass
class SchemaEnum:
    name: str
    values: list[str]


@dataclass
class SchemaState:
    dialect: str
    tables: list[SchemaTable] = field(default_factory=list)
    enums: list[SchemaEnum] = field(default_factory=list)
