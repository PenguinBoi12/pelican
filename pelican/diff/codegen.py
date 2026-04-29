from collections.abc import Sequence
from typing import Any

from .operations import (
    DiffOperation,
    CreateTable,
    DropTable,
    CreateEnum,
    DropEnum,
    AddEnumValue,
    RemoveEnumValue,
)

_INDENT = "    "
_INDENT_BLOCK = _INDENT * 2

_STANDALONE = (
    CreateTable,
    DropTable,
    CreateEnum,
    DropEnum,
    AddEnumValue,
    RemoveEnumValue,
)


def render_up(ops: Sequence[DiffOperation]) -> str:
    lines: list[str] = []

    for op in ops:
        if isinstance(op, (CreateEnum, AddEnumValue)):
            lines.extend(_INDENT + line for line in op.render_up())

    for op in _fk_sorted([op for op in ops if isinstance(op, CreateTable)]):
        lines.extend(_INDENT + line for line in op.render_up())

    for op in reversed(_fk_sorted([op for op in ops if isinstance(op, DropTable)])):
        lines.extend(_INDENT + line for line in op.render_up())

    for op in ops:
        if isinstance(op, (DropEnum, RemoveEnumValue)):
            lines.extend(_INDENT + line for line in op.render_up())

    for table_name, t_ops in sorted(_group_by_table(ops).items()):
        block = _render_change_table(table_name, t_ops, up=True)
        if block:
            lines.extend(block)

    return "\n".join(lines) if lines else f"{_INDENT}pass"


def render_down(ops: Sequence[DiffOperation]) -> str:
    lines: list[str] = []

    for op in reversed(list(ops)):
        if isinstance(op, (DropEnum, RemoveEnumValue)):
            lines.extend(_INDENT + line for line in op.render_down())

    for op in _fk_sorted([op for op in ops if isinstance(op, DropTable)]):
        lines.extend(_INDENT + line for line in op.render_down())

    for op in reversed(_fk_sorted([op for op in ops if isinstance(op, CreateTable)])):
        lines.extend(_INDENT + line for line in op.render_down())

    for op in reversed(list(ops)):
        if isinstance(op, (CreateEnum, AddEnumValue)):
            lines.extend(_INDENT + line for line in op.render_down())

    for table_name, t_ops in sorted(_group_by_table(ops).items()):
        block = _render_change_table(table_name, list(reversed(t_ops)), up=False)
        if block:
            lines.extend(block)

    return "\n".join(lines) if lines else f"{_INDENT}pass"


def _fk_sorted(ops: list[Any]) -> list[Any]:
    """Sort CreateTable/DropTable ops so referenced tables come before tables that reference them."""
    if len(ops) <= 1:
        return ops

    by_name = {op.table.name: op for op in ops}
    visited: set[str] = set()
    result: list[Any] = []

    def visit(name: str) -> None:
        if name in visited or name not in by_name:
            return
        visited.add(name)
        for fk in by_name[name].table.foreign_keys:
            visit(fk.ref_table)
        result.append(by_name[name])

    for name in sorted(by_name):
        visit(name)

    return result


def _render_change_table(
    table_name: str, ops: Sequence[DiffOperation], *, up: bool
) -> list[str]:
    inner = [
        _INDENT_BLOCK + line
        for op in ops
        for line in (op.render_up() if up else op.render_down())
    ]
    if not inner:
        return []
    return [f"{_INDENT}with change_table({table_name!r}) as t:"] + inner


def _group_by_table(ops: Sequence[DiffOperation]) -> dict[str, list[DiffOperation]]:
    result: dict[str, list[DiffOperation]] = {}
    for op in ops:
        if not isinstance(op, _STANDALONE) and hasattr(op, "table_name"):
            result.setdefault(op.table_name, []).append(op)
    return result
