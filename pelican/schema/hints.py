def renamed_from(old_name: str) -> dict:
    """Mark a column as renamed from `old_name` for pelican autogenerate.

    Usage::

        class User(SQLModel, table=True):
            full_name: str = Field(
                sa_column=Column(String(255), info=renamed_from("name"))
            )
    """
    return {"pelican_rename_from": old_name}
