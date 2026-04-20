from typing import Any, Iterable

from sqlalchemy.schema import DDL
from sqlalchemy.types import TypeEngine

from .compiler import DialectCompiler


class PostgreSQLCompiler(DialectCompiler):
    def rename_column(
        self, table_name: str, old_name: str, new_name: str
    ) -> Iterable[DDL]:
        return [DDL(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}")]

    def alter_column(
        self,
        table_name: str,
        column_name: str,
        new_type: TypeEngine | None = None,
        nullable: bool | None = None,
        default: Any = None,
        server_default: Any = None,
    ) -> Iterable[DDL]:
        statements = []

        if new_type is not None:
            type_str = self.dialect.type_compiler_instance.process(new_type)
            statements.append(
                DDL(
                    f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {type_str}"
                )
            )

        if nullable is True:
            statements.append(
                DDL(
                    f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP NOT NULL"
                )
            )
        elif nullable is False:
            statements.append(
                DDL(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL")
            )

        if server_default is not None:
            statements.append(
                DDL(
                    f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET DEFAULT {server_default}"
                )
            )

        if not statements:
            raise ValueError(
                f"alter_column for '{column_name}' requires at least one change "
                "(new_type, nullable, or server_default)"
            )

        return statements
