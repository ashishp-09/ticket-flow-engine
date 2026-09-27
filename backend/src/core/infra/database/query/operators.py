from typing import Any, Callable

from sqlalchemy import BinaryExpression, bindparam

OPERATORS: dict[str, Callable[[Any, Any], BinaryExpression]] = {
    "eq": lambda col, val: col == val,
    "between": lambda col, val: col.between(val[0], val[1]),
    "ieq": lambda col, val: col.ilike(str(val).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_'),
                                      escape="\\"),
    "ne": lambda col, val: col != val,
    "gte": lambda col, val: col >= val,
    "lte": lambda col, val: col <= val,
    "gt": lambda col, val: col > val,
    "lt": lambda col, val: col < val,
    "in": lambda col, val: col.in_(
        bindparam(f"exp_in_{col.name}", value=tuple(val) if isinstance(val, list) else val, expanding=True)
    ),
    "not_in": lambda col, val: ~col.in_(
        bindparam(f"exp_notin_{col.name}", value=tuple(val) if isinstance(val, list) else val, expanding=True)
    ),
    "contains": lambda col, val: col.like(
        f"%{str(val).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%",
        escape="\\"
    ),
    "icontains": lambda col, val: col.ilike(
        f"%{str(val).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%",
        escape="\\"
    ),
    "startswith": lambda col, val: col.like(
        f"{str(val).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%",
        escape="\\"
    ),
    "istartswith": lambda col, val: col.ilike(
        f"{str(val).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%",
        escape="\\"
    ),
    "endswith": lambda col, val: col.like(
        f"%{str(val).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}",
        escape="\\"
    ),
    "iendswith": lambda col, val: col.ilike(
        f"%{str(val).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}",
        escape="\\"
    ),
    "has_any": lambda col, val: col.any(),
    "is_null": lambda col, val: col.is_(None) if val else col.is_not(None),
    "is_not_null": lambda col, val: col.is_not(None) if val else col.is_(None),
}
