import importlib
import inspect
import sys
from pathlib import Path
from types import ModuleType

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


def load_target_metadata(import_path: str) -> MetaData:
    """Import `import_path` and return the combined MetaData from all models found."""
    # Ensure the user's project root is importable when pelican runs as a CLI tool
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    module = importlib.import_module(import_path)
    metadata = _find_metadata(module)

    if not metadata or not metadata.tables:
        raise ValueError(
            f"No SQLAlchemy models found in {import_path!r}.\n"
            "Make sure the module contains DeclarativeBase subclasses or a MetaData instance."
        )

    return metadata


def _find_metadata(module: ModuleType) -> MetaData | None:
    combined = MetaData()
    seen: set[int] = set()

    def _collect(metadata: MetaData) -> None:
        if id(metadata) in seen:
            return
        seen.add(id(metadata))
        for table in metadata.tables.values():
            if table.name not in combined.tables:
                table.tometadata(combined, schema=table.schema)

    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ != module.__name__:
            continue
        # SQLAlchemy 2.x DeclarativeBase subclasses
        if _is_declarative_base_subclass(obj) and hasattr(obj, "metadata"):
            _collect(obj.metadata)
        # SQLModel (table=True) and older declarative_base() style:
        # mapped classes always have __table__ attached after class creation
        elif hasattr(obj, "__table__") and hasattr(obj, "metadata"):
            _collect(obj.metadata)

    # Bare MetaData instances declared directly on the module
    for _name, obj in inspect.getmembers(module):
        if isinstance(obj, MetaData) and obj is not combined:
            _collect(obj)

    return combined if combined.tables else None


def _is_declarative_base_subclass(cls: type) -> bool:
    try:
        return issubclass(cls, DeclarativeBase) and cls is not DeclarativeBase
    except TypeError:
        return False
