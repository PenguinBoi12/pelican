from os import environ
from dotenv import load_dotenv
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, MetaData


class MigrationRunner:
    def __init__(self):
        load_dotenv(".env")

        self._engine: Engine | None = None
        self._metadata: MetaData | None = None
        self._session: Session | None = None

        self._database_url: str | None = None

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
