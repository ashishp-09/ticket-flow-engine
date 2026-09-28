import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from src.core.settings import get_settings

security = HTTPBearer()
SecurityDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]


def verify_metrics_token(credentials: SecurityDep):
    if not secrets.compare_digest(credentials.credentials, get_settings().metrics_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def init_metrics(app: FastAPI) -> None:
    Instrumentator().instrument(app=app)

    @app.get("/metrics", dependencies=[Depends(verify_metrics_token)], tags=["Monitoring"])
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
