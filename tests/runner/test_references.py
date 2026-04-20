import pytest
from sqlalchemy import inspect

from pelican import create_table
from pelican.runner import MigrationRunner


@pytest.mark.parametrize(
    "model_name,expected_table",
    [
        ("user", "users"),
        ("category", "categories"),
        ("child", "children"),
        ("person", "people"),
        ("sheep", "sheep"),
    ],
)
def test_references__with_model_name__expect_fk_to_plural_table(
    model_name: str, expected_table: str, db_runner: MigrationRunner
) -> None:
    with create_table(expected_table) as t:
        t.string("name")

    with create_table("posts") as t:
        t.string("title")
        t.references(model_name)

    fks = inspect(db_runner.engine).get_foreign_keys("posts")
    assert any(fk["referred_table"] == expected_table for fk in fks)
