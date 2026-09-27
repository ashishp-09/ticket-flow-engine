from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import func, inspect, select

from ..expressions.base import BaseExpression


class SQLFunction(ABC):
    @abstractmethod
    def resolve(self, current_model: Any) -> Any:
        pass


class Count(SQLFunction):
    def __init__(self, relationship: Any):
        self.relationship = relationship

    def resolve(self, current_model: Any) -> Any:
        resolved_rel = self.relationship.resolve(current_model) if isinstance(self.relationship,
                                                                              BaseExpression) else self.relationship
        prop = inspect(resolved_rel).property
        target_model = prop.mapper.class_
        return (
            select(func.count())
            .select_from(target_model)
            .where(prop.primaryjoin)
            .correlate(current_model)
            .scalar_subquery()
        )
