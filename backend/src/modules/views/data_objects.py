from dataclasses import dataclass
from typing import NamedTuple, Optional

from src.core.infra.database import BaseDTO


@dataclass
class ViewLogDTO(BaseDTO):
    id: int
    object_type: str
    object_id: int

    user_id: Optional[int] = None


class VisitorData(NamedTuple):
    ip_address: str
    user_agent: str
