from dataclasses import dataclass
from functools import reduce

from .schema import SchemaState
from .operations import DiffOperation
from .differ import diff as _diff


@dataclass
class ValidationResult:
    is_valid: bool
    discrepancies: list[DiffOperation]


def validate(
    current: SchemaState,
    desired: SchemaState,
    ops: list[DiffOperation],
) -> ValidationResult:
    simulated = reduce(lambda s, op: op.apply(s), ops, current)
    remaining = _diff(simulated, desired).all_ops()
    return ValidationResult(is_valid=not remaining, discrepancies=remaining)
