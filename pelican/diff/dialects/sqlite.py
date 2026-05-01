from .base import DialectInspector


class SQLiteInspector(DialectInspector):
    def filter_indexes(self, indexes: list[dict]) -> list[dict]:
        return [
            idx
            for idx in indexes
            if not (idx.get("name") or "").startswith("sqlite_autoindex_")
        ]
