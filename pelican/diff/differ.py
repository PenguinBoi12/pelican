from dataclasses import dataclass
from difflib import SequenceMatcher

from .schema import SchemaState, SchemaTable, SchemaColumn
from .operations import (
    DiffOperation,
    CreateTable,
    DropTable,
    AddColumn,
    DropColumn,
    RenameColumn,
    AlterColumnType,
    AlterColumnNullable,
    AlterColumnServerDefault,
    CreateIndex,
    DropIndex,
    AddCheckConstraint,
    DropCheckConstraint,
    CreateEnum,
    DropEnum,
    AddEnumValue,
    RemoveEnumValue,
)

_RENAME_THRESHOLD = 0.7


@dataclass
class DiffResult:
    ops: list[DiffOperation]
    renames: list[RenameColumn]

    def __bool__(self) -> bool:
        return bool(self.ops or self.renames)


def diff(current: SchemaState, desired: SchemaState) -> DiffResult:
    all_ops: list[DiffOperation] = []
    all_ops.extend(_diff_enums(current, desired))
    all_ops.extend(_diff_tables(current, desired))
    renames = [op for op in all_ops if isinstance(op, RenameColumn)]
    ops: list[DiffOperation] = [
        op for op in all_ops if not isinstance(op, RenameColumn)
    ]
    return DiffResult(ops=ops, renames=renames)


def _diff_enums(current: SchemaState, desired: SchemaState) -> list[DiffOperation]:
    ops: list[DiffOperation] = []
    current_enums = {e.name: e for e in current.enums}
    desired_enums = {e.name: e for e in desired.enums}

    for name in desired_enums.keys() - current_enums.keys():
        ops.append(CreateEnum(desired_enums[name]))

    for name in current_enums.keys() - desired_enums.keys():
        ops.append(DropEnum(current_enums[name]))

    for name in current_enums.keys() & desired_enums.keys():
        cur_vals = current_enums[name].values
        des_vals = desired_enums[name].values
        cur_set = set(cur_vals)
        des_set = set(des_vals)
        for v in des_vals:
            if v not in cur_set:
                ops.append(AddEnumValue(name, v))
        for v in cur_vals:
            if v not in des_set:
                ops.append(RemoveEnumValue(name, v))

    return ops


def _diff_tables(current: SchemaState, desired: SchemaState) -> list[DiffOperation]:
    ops: list[DiffOperation] = []
    current_tables = {t.name: t for t in current.tables}
    desired_tables = {t.name: t for t in desired.tables}

    for name in desired_tables.keys() - current_tables.keys():
        ops.append(CreateTable(desired_tables[name]))

    for name in current_tables.keys() - desired_tables.keys():
        ops.append(DropTable(current_tables[name]))

    for name in current_tables.keys() & desired_tables.keys():
        ops.extend(_diff_table(current_tables[name], desired_tables[name]))

    return ops


def _diff_table(current: SchemaTable, desired: SchemaTable) -> list[DiffOperation]:
    ops: list[DiffOperation] = []
    ops.extend(_diff_columns(current, desired))
    ops.extend(_diff_indexes(current, desired))
    ops.extend(_diff_check_constraints(current, desired))
    return ops


def _diff_columns(current: SchemaTable, desired: SchemaTable) -> list[DiffOperation]:
    ops: list[DiffOperation] = []
    current_cols = {c.name: c for c in current.columns}
    desired_cols = {c.name: c for c in desired.columns}

    disappeared = [c for c in current.columns if c.name not in desired_cols]
    appeared = [c for c in desired.columns if c.name not in current_cols]

    renames, remaining_disappeared, remaining_appeared = _detect_renames(
        current.name, disappeared, appeared, len(current.columns)
    )
    ops.extend(renames)

    for col in remaining_disappeared:
        ops.append(DropColumn(current.name, col))

    for col in remaining_appeared:
        ops.append(AddColumn(desired.name, col))

    # Diff common columns for type/nullable/server_default changes
    for name in current_cols.keys() & desired_cols.keys():
        ops.extend(_diff_column(current.name, current_cols[name], desired_cols[name]))

    return ops


def _diff_column(
    table_name: str, current: SchemaColumn, desired: SchemaColumn
) -> list[DiffOperation]:
    ops: list[DiffOperation] = []

    if current.type != desired.type:
        ops.append(
            AlterColumnType(table_name, current.name, current.type, desired.type)
        )

    if current.nullable != desired.nullable:
        ops.append(
            AlterColumnNullable(
                table_name, current.name, current.nullable, desired.nullable
            )
        )

    if current.server_default != desired.server_default:
        ops.append(
            AlterColumnServerDefault(
                table_name, current.name, current.server_default, desired.server_default
            )
        )

    return ops


def _detect_renames(
    table_name: str,
    disappeared: list[SchemaColumn],
    appeared: list[SchemaColumn],
    total_cols: int,
) -> tuple[list[RenameColumn], list[SchemaColumn], list[SchemaColumn]]:
    renames: list[RenameColumn] = []
    remaining_disappeared = list(disappeared)
    remaining_appeared = list(appeared)

    if not remaining_disappeared or not remaining_appeared:
        return renames, remaining_disappeared, remaining_appeared

    # Score all pairs
    pairs: list[tuple[float, SchemaColumn, SchemaColumn]] = []
    for dis in remaining_disappeared:
        for app in remaining_appeared:
            score = _rename_score(dis, app, total_cols)
            if score >= _RENAME_THRESHOLD:
                pairs.append((score, dis, app))

    # Greedy assignment: highest score first
    pairs.sort(key=lambda x: x[0], reverse=True)
    matched_dis: set[str] = set()
    matched_app: set[str] = set()

    for score, dis, app in pairs:
        if dis.name in matched_dis or app.name in matched_app:
            continue
        renames.append(
            RenameColumn(
                table_name=table_name,
                old_name=dis.name,
                new_name=app.name,
                confidence=score,
                old_col=dis,
                new_col=app,
            )
        )
        matched_dis.add(dis.name)
        matched_app.add(app.name)

    remaining_disappeared = [
        c for c in remaining_disappeared if c.name not in matched_dis
    ]
    remaining_appeared = [c for c in remaining_appeared if c.name not in matched_app]

    return renames, remaining_disappeared, remaining_appeared


def _rename_score(
    disappeared: SchemaColumn, appeared: SchemaColumn, total_cols: int
) -> float:
    type_match = 0.40 if disappeared.type == appeared.type else 0.0
    nullable_match = 0.15 if disappeared.nullable == appeared.nullable else 0.0

    pos_diff = abs(disappeared.position - appeared.position)
    denom = max(total_cols - 1, 1)
    position_score = 0.15 * (1.0 - min(pos_diff / denom, 1.0))

    name_ratio = SequenceMatcher(None, disappeared.name, appeared.name).ratio()
    name_score = 0.30 * name_ratio

    return type_match + nullable_match + position_score + name_score


def _diff_indexes(current: SchemaTable, desired: SchemaTable) -> list[DiffOperation]:
    ops: list[DiffOperation] = []
    current_idxs = {i.name: i for i in current.indexes}
    desired_idxs = {i.name: i for i in desired.indexes}

    for name in desired_idxs.keys() - current_idxs.keys():
        ops.append(CreateIndex(desired.name, desired_idxs[name]))

    for name in current_idxs.keys() - desired_idxs.keys():
        ops.append(DropIndex(current.name, current_idxs[name]))

    return ops


def _diff_check_constraints(
    current: SchemaTable, desired: SchemaTable
) -> list[DiffOperation]:
    ops: list[DiffOperation] = []
    # Compare by normalized expression since names may differ between DB and model
    current_exprs = {cc.expression: cc for cc in current.check_constraints}
    desired_exprs = {cc.expression: cc for cc in desired.check_constraints}

    for expr in desired_exprs.keys() - current_exprs.keys():
        ops.append(AddCheckConstraint(desired.name, desired_exprs[expr]))

    for expr in current_exprs.keys() - desired_exprs.keys():
        ops.append(DropCheckConstraint(current.name, current_exprs[expr]))

    return ops
