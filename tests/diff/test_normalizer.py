import pytest
from pelican.diff.normalizer import (
    normalize_type,
    normalize_check_expression,
    normalize_server_default,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("VARCHAR(255)", "VARCHAR(255)"),
        ("varchar(255)", "VARCHAR(255)"),
        ("CHARACTER VARYING(255)", "VARCHAR(255)"),
        ("character varying(255)", "VARCHAR(255)"),
        ("CHARACTER VARYING", "TEXT"),
        ("INTEGER", "INTEGER"),
        ("INT", "INTEGER"),
        ("INT4", "INTEGER"),
        ("INT2", "SMALLINT"),
        ("SMALLINT", "SMALLINT"),
        ("INT8", "BIGINT"),
        ("BIGINT", "BIGINT"),
        ("BOOL", "BOOLEAN"),
        ("BOOLEAN", "BOOLEAN"),
        ("DOUBLE PRECISION", "DOUBLE"),
        ("FLOAT8", "DOUBLE"),
        ("REAL", "REAL"),
        ("FLOAT4", "REAL"),
        ("TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP"),
        ("TIMESTAMP", "TIMESTAMP"),
        ("TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ"),
        ("TIMESTAMPTZ", "TIMESTAMPTZ"),
        # MySQL-style display widths stripped
        ("INTEGER(11)", "INTEGER"),
        ("BIGINT(20)", "BIGINT"),
        # Meaningful params preserved
        ("NUMERIC(10, 2)", "NUMERIC(10, 2)"),
        ("CHAR(1)", "CHAR(1)"),
        # Postgres-specific types pass through unchanged
        ("TEXT", "TEXT"),
        ("JSONB", "JSONB"),
        ("UUID", "UUID"),
        ("BYTEA", "BYTEA"),
    ],
)
def test_normalize_type__with_alias__expect_canonical(raw: str, expected: str) -> None:
    assert normalize_type(raw) == expected


def test_normalize_type__with_interval__expect_unchanged() -> None:
    # INT inside INTERVAL must not be replaced
    assert normalize_type("INTERVAL") == "INTERVAL"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("now()", "now()"),
        ("(now())", "now()"),
        ("NOW()", "now()"),
        ("'active'::character varying", "'active'"),
        ("'active'::text", "'active'"),
        ("(42)", "42"),
        ("'true'", "true"),
        ("'false'", "false"),
        ("true", "true"),
        ("false", "false"),
    ],
)
def test_normalize_server_default__with_expr__expect_canonical(
    raw: str, expected: str
) -> None:
    assert normalize_server_default(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("age > 0", "age > 0"),
        ("(age > 0)", "age > 0"),
        ('"age" > 0', "age > 0"),
        ("  AGE  >  0  ", "age > 0"),
        ('("age" > 0)', "age > 0"),
        ("LENGTH(name) > 0", "length(name) > 0"),
    ],
)
def test_normalize_check_expression__with_expr__expect_canonical(
    raw: str, expected: str
) -> None:
    assert normalize_check_expression(raw) == expected
