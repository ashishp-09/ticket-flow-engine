from typing import Any, Type, NamedTuple


class ResolvedFilter(NamedTuple):
    column: Any
    relations: list[Any]
    operator: str


class FilterResolver:
    @staticmethod
    def resolve(model: Type[Any], key: str, operators_map: dict[str, Any]) -> ResolvedFilter:
        path, operator = key.split("__", 1) if "__" in key else (key, "eq")
        if operator not in operators_map:
            path = key
            operator = "eq"

        parts = path.split("__")
        field_name = parts.pop()

        current_model = model
        relations = []

        for relation_name in parts:
            if hasattr(current_model, relation_name):
                rel_attr = getattr(current_model, relation_name)
                if hasattr(rel_attr, "property") and hasattr(rel_attr.property, "mapper"):
                    relations.append(rel_attr)
                    current_model = rel_attr.property.mapper.class_

        column = getattr(current_model, field_name, None)
        return ResolvedFilter(column=column, relations=relations, operator=operator)
