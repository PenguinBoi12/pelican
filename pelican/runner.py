from os import environ
from dotenv import load_dotenv
from datetime import datetime
from typing import Iterator
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import inspect, create_engine, MetaData
from sqlmodel import SQLModel, Session as SQLModelSession, Field, select


class _SchemaMigration(SQLModel, table=True):
    __tablename__ = "pelican_migration"

    version: int = Field(primary_key=True)
    applied_at: datetime = Field(default_factory=datetime.now, nullable=False)


class MigrationRunner:
    def __init__(self):
        load_dotenv(".env")

        self._engine: Engine | None = None
        self._metadata: MetaData | None = None
        self._session: Session | None = None
        self._database_url: str | None = None

        self.ensure_version_table_exists()

    @property
    def database_url(self) -> str:
        if not self._database_url:
            self._database_url = environ.get("DATABASE_URL", "sqlite:///database.db")
        return self._database_url

    @property
    def engine(self) -> Engine:
        if not self._engine:
            self._engine = create_engine(self.database_url)
        return self._engine

    @property
    def metadata(self) -> MetaData:
        if not self._metadata:
            self._metadata = MetaData()
        return self._metadata

    @property
    def session(self) -> Session:
        if not self._session:
            session_maker: sessionmaker = sessionmaker(bind=self._engine)
            self._session = session_maker()
        return self._session

    def ensure_version_table_exists(self) -> None:
        inspector = inspect(self.engine)
        if "pelican_migration" not in inspector.get_table_names():
            SQLModel.metadata.create_all(
                self.engine, tables=[_SchemaMigration.__table__]
            )

    def get_applied_versions(self) -> Iterator[int]:
        with SQLModelSession(self.engine) as s:
            for version in s.exec(select(_SchemaMigration.version)):
                yield int(version)

    def record_applied(self, version: int) -> None:
        self.session.add(_SchemaMigration(version=version))
        self.session.commit()

    def record_unapplied(self, version: int) -> None:
        self.session.query(_SchemaMigration).filter_by(version=version).delete()
        self.session.commit()
