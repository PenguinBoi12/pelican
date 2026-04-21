import pytest
from sqlalchemy import create_engine, text

from pelican.diff.inspector import introspect_live_db
from pelican.diff.schema import SchemaState


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:")
    with e.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) NOT NULL,
                bio TEXT,
                score FLOAT
            )
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX users_email_idx ON users (email)
        """))
        conn.execute(text("""
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255) NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """))
    return e


def test_introspect_live_db__expect_schema_state(engine) -> None:
    state = introspect_live_db(engine)
    assert isinstance(state, SchemaState)
    assert state.dialect == "sqlite"


def test_introspect_live_db__expect_tables_found(engine) -> None:
    state = introspect_live_db(engine)
    names = [t.name for t in state.tables]
    assert "users" in names
    assert "posts" in names


def test_introspect_live_db__expect_pelican_migration_excluded(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE pelican_migration (version INTEGER PRIMARY KEY)
        """))
    state = introspect_live_db(engine)
    names = [t.name for t in state.tables]
    assert "pelican_migration" not in names


def test_introspect_live_db__expect_columns_inspected(engine) -> None:
    state = introspect_live_db(engine)
    users = next(t for t in state.tables if t.name == "users")
    col_names = [c.name for c in users.columns]
    assert col_names == ["id", "email", "bio", "score"]


def test_introspect_live_db__expect_primary_key_detected(engine) -> None:
    state = introspect_live_db(engine)
    users = next(t for t in state.tables if t.name == "users")
    id_col = next(c for c in users.columns if c.name == "id")
    assert id_col.primary_key is True


def test_introspect_live_db__expect_nullable_detected(engine) -> None:
    state = introspect_live_db(engine)
    users = next(t for t in state.tables if t.name == "users")
    email_col = next(c for c in users.columns if c.name == "email")
    bio_col = next(c for c in users.columns if c.name == "bio")
    assert email_col.nullable is False
    assert bio_col.nullable is True


def test_introspect_live_db__expect_index_found(engine) -> None:
    state = introspect_live_db(engine)
    users = next(t for t in state.tables if t.name == "users")
    idx = next((i for i in users.indexes if i.name == "users_email_idx"), None)
    assert idx is not None
    assert idx.unique is True
    assert idx.columns == ["email"]


def test_introspect_live_db__expect_type_normalized(engine) -> None:
    state = introspect_live_db(engine)
    users = next(t for t in state.tables if t.name == "users")
    email_col = next(c for c in users.columns if c.name == "email")
    assert email_col.type == "VARCHAR(255)"


def test_introspect_live_db__expect_column_positions(engine) -> None:
    state = introspect_live_db(engine)
    users = next(t for t in state.tables if t.name == "users")
    positions = [c.position for c in users.columns]
    assert positions == list(range(len(users.columns)))
