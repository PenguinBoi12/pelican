import pytest
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    MetaData,
    Table,
    ForeignKey,
    CheckConstraint,
    Index,
    create_engine,
    text,
)
from sqlalchemy.dialects import sqlite as sqlite_dialect

from pelican.diff.extractor import extract_from_metadata
from pelican.diff.schema import SchemaState

_DIALECT = sqlite_dialect.dialect()


def _make_metadata(*tables: Table) -> MetaData:
    metadata = MetaData()
    for t in tables:
        t.tometadata(metadata)
    return metadata


@pytest.fixture
def simple_metadata() -> MetaData:
    metadata = MetaData()
    Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("email", String(255), nullable=False),
        Column("bio", Text, nullable=True),
    )
    return metadata


def test_extract_from_metadata__expect_schema_state(simple_metadata: MetaData) -> None:
    state = extract_from_metadata(simple_metadata, _DIALECT)
    assert isinstance(state, SchemaState)
    assert state.dialect == "sqlite"


def test_extract_from_metadata__expect_table_found(simple_metadata: MetaData) -> None:
    state = extract_from_metadata(simple_metadata, _DIALECT)
    assert any(t.name == "users" for t in state.tables)


def test_extract_from_metadata__expect_columns_extracted(
    simple_metadata: MetaData,
) -> None:
    state = extract_from_metadata(simple_metadata, _DIALECT)
    users = next(t for t in state.tables if t.name == "users")
    col_names = [c.name for c in users.columns]
    assert col_names == ["id", "email", "bio"]


def test_extract_from_metadata__expect_primary_key_detected(
    simple_metadata: MetaData,
) -> None:
    state = extract_from_metadata(simple_metadata, _DIALECT)
    users = next(t for t in state.tables if t.name == "users")
    id_col = next(c for c in users.columns if c.name == "id")
    assert id_col.primary_key is True


def test_extract_from_metadata__expect_nullable_extracted(
    simple_metadata: MetaData,
) -> None:
    state = extract_from_metadata(simple_metadata, _DIALECT)
    users = next(t for t in state.tables if t.name == "users")
    email_col = next(c for c in users.columns if c.name == "email")
    bio_col = next(c for c in users.columns if c.name == "bio")
    assert email_col.nullable is False
    assert bio_col.nullable is True


def test_extract_from_metadata__expect_type_normalized(
    simple_metadata: MetaData,
) -> None:
    state = extract_from_metadata(simple_metadata, _DIALECT)
    users = next(t for t in state.tables if t.name == "users")
    email_col = next(c for c in users.columns if c.name == "email")
    assert email_col.type == "VARCHAR(255)"


def test_extract_from_metadata__expect_index_extracted() -> None:
    metadata = MetaData()
    t = Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("email", String(255)),
    )
    Index("users_email_idx", t.c.email, unique=True)

    state = extract_from_metadata(metadata, _DIALECT)
    users = next(t for t in state.tables if t.name == "users")
    idx = next((i for i in users.indexes if i.name == "users_email_idx"), None)
    assert idx is not None
    assert idx.unique is True
    assert idx.columns == ["email"]


def test_extract_from_metadata__expect_check_constraint_extracted() -> None:
    metadata = MetaData()
    Table(
        "products",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("price", Integer),
        CheckConstraint("price > 0", name="products_price_positive"),
    )

    state = extract_from_metadata(metadata, _DIALECT)
    products = next(t for t in state.tables if t.name == "products")
    cc = next(
        (c for c in products.check_constraints if c.name == "products_price_positive"),
        None,
    )
    assert cc is not None
    assert cc.expression == "price > 0"


def test_extract_from_metadata__expect_foreign_key_extracted() -> None:
    metadata = MetaData()
    Table("users", metadata, Column("id", Integer, primary_key=True))
    Table(
        "posts",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    )

    state = extract_from_metadata(metadata, _DIALECT)
    posts = next(t for t in state.tables if t.name == "posts")
    fk = next((f for f in posts.foreign_keys if "user_id" in f.columns), None)
    assert fk is not None
    assert fk.ref_table == "users"
    assert fk.ref_columns == ["id"]
    assert fk.on_delete == "CASCADE"


def test_extract_from_metadata__expect_column_positions() -> None:
    metadata = MetaData()
    Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(255)),
        Column("email", String(255)),
    )
    state = extract_from_metadata(metadata, _DIALECT)
    users = next(t for t in state.tables if t.name == "users")
    assert [c.position for c in users.columns] == [0, 1, 2]
