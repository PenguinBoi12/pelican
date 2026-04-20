from typing import Any, Iterable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from sqlalchemy.types import TypeEngine
from sqlalchemy.sql import Executable
from sqlalchemy import Column
from pelican.compilers import DialectCompiler


@dataclass
class Operation(ABC):
    table_name: str

    @abstractmethod
    def compile(self, compiler: DialectCompiler) -> Iterable[Executable]:
        pass


@dataclass
class AddColumn(Operation):
    column: Column

    def compile(self, compiler: DialectCompiler) -> Iterable[Executable]:
        return compiler.add_column(self.table_name, self.column)


@dataclass
class DropColumn(Operation):
    column_name: str

    def compile(self, compiler: DialectCompiler) -> Iterable[Executable]:
        return compiler.drop_column(self.table_name, self.column_name)


@dataclass
class RenameColumn(Operation):
    old_name: str
    new_name: str

    def compile(self, compiler: DialectCompiler) -> Iterable[Executable]:
        return compiler.rename_column(self.table_name, self.old_name, self.new_name)


@dataclass
class AlterColumn(Operation):
    column_name: str
    new_type: TypeEngine | None = None
    nullable: bool | None = None
    default: Any = None
    server_default: Any = None

    def compile(self, compiler: DialectCompiler) -> Iterable[Executable]:
        return compiler.alter_column(
            self.table_name,
            self.column_name,
            new_type=self.new_type,
            nullable=self.nullable,
            default=self.default,
            server_default=self.server_default,
        )


@dataclass
class CreateIndex(Operation):
    index_name: str
    column_names: list[str]
    unique: bool

    def compile(self, compiler: DialectCompiler) -> Iterable[Executable]:
        return compiler.create_index(
            self.table_name, self.index_name, self.column_names, self.unique
        )


@dataclass
class RemoveIndex(Operation):
    index_name: str

    def compile(self, compiler: DialectCompiler) -> Iterable[Executable]:
        return compiler.drop_index(self.table_name, self.index_name)
