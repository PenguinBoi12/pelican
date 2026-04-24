from os import environ
from datetime import datetime
from collections.abc import Iterator, Iterable
from typing import TYPE_CHECKING

from sqlalchemy import inspect, create_engine, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Executable, DDLElement
from sqlalchemy.sql.elements import TextClause
from sqlmodel import SQLModel, Session, Field, select

from ._types import Migration
from .compilers import DialectCompiler, PostgreSQLCompiler, SQLiteCompiler

if TYPE_CHECKING:
    from .schema.operations import Operation


_DIALECT_COMPILERS: dict[str, type[DialectCompiler]] = {
    "sqlite": SQLiteCompiler,
    "postgresql": PostgreSQLCompiler,
}


def _build_compiler(engine: Engine) -> DialectCompiler:
    dialect_name = engine.dialect.name
    compiler_cls = _DIALECT_COMPILERS.get(dialect_name)

    if not compiler_cls:
        raise ValueError(
            f"Unsupported dialect: {dialect_name}. "
            f"Supported dialects: {', '.join(_DIALECT_COMPILERS.keys())}"
        )

    return compiler_cls(engine)


class _SchemaMigration(SQLModel, table=True):
    __tablename__ = "pelican_migration"

    version: int = Field(primary_key=True)
    applied_at: datetime = Field(default_factory=datetime.now, nullable=False)


class MigrationRunner:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url: str | None = None
        self._engine: Engine | None = None
        self._compiler: DialectCompiler | None = None

        self.metadata: MetaData = SQLModel.metadata
        if url := database_url or environ.get("DATABASE_URL"):
            self.database_url = url

    @property
    def database_url(self) -> str:
        if self._database_url is None:
            raise RuntimeError("Database url is not set.")
        return self._database_url

    @database_url.setter
    def database_url(self, url: str) -> None:
        self._database_url = url
        self._engine = create_engine(url)
        self._compiler = _build_compiler(self._engine)

    @property
    def has_database_url(self) -> bool:
        """Whether a database URL has been configured on this runner."""
        return self._database_url is not None

    @property
    def engine(self) -> Engine:
        assert self._engine is not None, "Database engine not initialized"
        return self._engine

    @property
    def compiler(self) -> DialectCompiler:
        assert self._compiler is not None, "Database compiler not initialized"
        return self._compiler

    def get_applied_versions(self) -> Iterator[int]:
        self._ensure_version_table_exists()

        with Session(self.engine) as s:
            for version in s.exec(select(_SchemaMigration.version)):
                yield int(version)

    def upgrade(self, migration: Migration) -> None:
        if not migration.up:
            raise ValueError("Migration has no upgrade function")

        migration.up()
        self._record_applied(migration.revision)

    def downgrade(self, migration: Migration) -> None:
        if not migration.down:
            raise ValueError("Migration has no downgrade function")

        migration.down()
        self._record_unapplied(migration.revision)

    def execute(self, ddls: Iterable[str | Executable | TextClause]) -> None:
        compiled_statements: list[tuple[str, dict]] = []

        for ddl in ddls:
            if isinstance(ddl, str):
                compiled_statements.append((ddl, {}))
            elif isinstance(ddl, (DDLElement, TextClause)):
                compiled = ddl.compile(dialect=self.engine.dialect)
                sql = compiled.string
                params = compiled.params or {}
                compiled_statements.append((sql, params))
            else:
                raise TypeError(f"Unsupported DDL type: {type(ddl)}")

        with self.engine.connect() as conn:
            with conn.begin():
                for sql, params in compiled_statements:
                    conn.exec_driver_sql(sql, params)

    def execute_operations(self, operations: Iterable["Operation"]) -> None:
        compiled_ddls = []

        for operation in operations:
            ddls = operation.compile(self.compiler)
            compiled_ddls.extend(list(ddls))

        self.execute(compiled_ddls)

    def _ensure_version_table_exists(self) -> None:
        inspector = inspect(self.engine)
        if "pelican_migration" not in inspector.get_table_names():
            _SchemaMigration.metadata.create_all(self.engine)

    def _record_applied(self, version: int) -> None:
        self._ensure_version_table_exists()

        with Session(self.engine) as session:
            session.add(_SchemaMigration(version=version))
            session.commit()

    def _record_unapplied(self, version: int) -> None:
        self._ensure_version_table_exists()

        with Session(self.engine) as session:
            statement = select(_SchemaMigration).where(
                _SchemaMigration.version == version
            )
            results = session.exec(statement)
            revision = results.one()

            session.delete(revision)
            session.commit()
