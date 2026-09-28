from typing import Any


def generate_error_values_for_int(
        min_value: int | None = None,
        max_value: int | None = None,
        extra_values: list[Any] | None = None
) -> list[Any]:
    values = ["abc"]
    if min_value is not None:
        values.append(min_value - 1)
    if max_value is not None:
        values.append(max_value + 1)
    if extra_values is not None:
        values.extend(extra_values)
    return values


def generate_error_values_for_str(max_length: int | None = None, extra_values: list[Any] | None = None) -> list[Any]:
    base = [" ", ""]
    if max_length is not None:
        base.append("a" * (max_length + 1))
    if extra_values is not None:
        base.extend(extra_values)
    return base


def generate_error_values_for_list(element_type: type = int) -> list[Any]:
    generic_bad_structures = [
        [],
        [[]],
        [{}],
        [{"id": 1}],
        None,
        "",
        0,
        -1,
        1,
        False,
        True,
        {},
        {"ids": [1]},
        (1, 2),
        [1, [2]],
    ]

    type_specific_errors: dict[type, list[Any]] = {
        int: [
            ["string"],
            [1, "2", 3],
            [1.5],
            [2.0],
            [None],
            [1, None, 3],
            [True],
            [1, False],
            ["-1"],
            ["0x1F"],
            [float("inf")],
            [float("nan")],
        ],
        str: [
            ["a", 2, "c"],
            [None],
            ["valid", None],
            [True],
            [1.5],
            [b"bytes"],
        ],
        float: [
            ["string"],
            [1, "2.5"],
            [None],
            [True],
        ]
    }

    bad_elements = type_specific_errors.get(element_type, [["unexpected_type_error"]])
    return generic_bad_structures + bad_elements


def generate_error_values_for_order_by(real_but_forbidden_field: str | None = None) -> list[int | str]:
    values = generate_error_values_for_str(max_length=100)
    values.append("nonexistent_field")

    if real_but_forbidden_field is not None:
        values.append(real_but_forbidden_field)

    return values


def generate_error_values_for_awaredatetime() -> list[int | str]:
    return [
        "not-a-date",
        "31-12-2026",
        "2026/12/31",
        "2026-13-01",
    ]
