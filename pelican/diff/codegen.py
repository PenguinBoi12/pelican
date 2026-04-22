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


def render_up(ops: list[DiffOperation]) -> str:
    lines: list[str] = []

    for op in ops:
        if isinstance(op, _STANDALONE):
            lines.extend(_INDENT + line for line in op.render_up())

    for table_name, t_ops in sorted(_group_by_table(ops).items()):
        block = _render_change_table(table_name, t_ops, up=True)
        if block:
            lines.extend(block)

    return "\n".join(lines) if lines else f"{_INDENT}pass"


def render_down(ops: list[DiffOperation]) -> str:
    lines: list[str] = []

    for op in reversed(ops):
        if isinstance(op, _STANDALONE):
            lines.extend(_INDENT + line for line in op.render_down())

    for table_name, t_ops in sorted(_group_by_table(ops).items()):
        block = _render_change_table(table_name, list(reversed(t_ops)), up=False)
        if block:
            lines.extend(block)

    return "\n".join(lines) if lines else f"{_INDENT}pass"


def _render_change_table(
    table_name: str, ops: list[DiffOperation], *, up: bool
) -> list[str]:
    inner = [
        _INDENT_BLOCK + line
        for op in ops
        for line in (op.render_up() if up else op.render_down())
    ]
    if not inner:
        return []
    return [f"{_INDENT}with change_table({table_name!r}) as t:"] + inner


def _group_by_table(ops: list[DiffOperation]) -> dict[str, list[DiffOperation]]:
    result: dict[str, list[DiffOperation]] = {}
    for op in ops:
        if not isinstance(op, _STANDALONE) and hasattr(op, "table_name"):
            result.setdefault(op.table_name, []).append(op)
    return result
