from typing import Annotated

from faststream import Depends

from src.modules.views.dependencies import get_view_log_service
from src.modules.views.services import ViewLogService

ViewLogServiceDep = Annotated[ViewLogService, Depends(get_view_log_service)]
