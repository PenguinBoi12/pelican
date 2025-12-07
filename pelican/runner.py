from os import environ
from dotenv import load_dotenv
from datetime import datetime
from typing import Iterator

from sqlalchemy import inspect, create_engine, MetaData
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session, Field, select

from .migration import Migration
from .compilers import DialectCompiler, SQLiteCompiler


_DIALECT_COMPILERS: dict[str, type[DialectCompiler]] = {
    "sqlite": SQLiteCompiler,
}


class _SchemaMigration(SQLModel, table=True):
    __tablename__ = "pelican_migration"

    version: int = Field(primary_key=True)
    applied_at: datetime = Field(default_factory=datetime.now, nullable=False)


class MigrationRunner:
    def __init__(self) -> None:
        load_dotenv(".env")

        self.database_url: str = environ.get("DATABASE_URL", "sqlite:///database.db")
        self.engine: Engine = create_engine(self.database_url)
        self.metadata: MetaData = SQLModel.metadata

        dialect_name = self.engine.dialect.name
        compiler_cls = _DIALECT_COMPILERS.get(dialect_name)

        if not compiler_cls:
            raise ValueError(
                f"Unsupported dialect: {dialect_name}. "
                f"Supported dialects: {', '.join(_DIALECT_COMPILERS.keys())}"
            )
        self.compiler = compiler_cls(self.engine)

        self._ensure_version_table_exists()

    def _ensure_version_table_exists(self) -> None:
        inspector = inspect(self.engine)
        if "pelican_migration" not in inspector.get_table_names():
            _SchemaMigration.metadata.create_all(self.engine)

    def get_applied_versions(self) -> Iterator[int]:
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

    def _record_applied(self, version: int) -> None:
        with Session(self.engine) as session:
            session.add(_SchemaMigration(version=version))
            session.commit()

    def _record_unapplied(self, version: int) -> None:
        with Session(self.engine) as session:
            statement = select(_SchemaMigration).where(_SchemaMigration.version == version)
            results = session.exec(statement)
            revision = results.one()

            session.delete(revision)
            session.commit()