from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infra.database.orm import AbstractORMModel


class ViewLog(AbstractORMModel):
    object_type: Mapped[str] = mapped_column(String(255))
    object_id: Mapped[int] = mapped_column(Integer())
    visitor_hash: Mapped[str] = mapped_column(String(32), index=True)

    __table_args__ = (
        UniqueConstraint(
            "object_type",
            "object_id",
            "visitor_hash",
            name="uq_view_logs_object_visitor"
        ),
    )
