from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.infra.transport.http.dependencies import JWTManagerDep
from .models import UserRole

user_auth_scheme = HTTPBearer(scheme_name="User_JWT_Token", auto_error=False)


class RoleChecker:
    def __init__(self, required_role: UserRole | None = None, optional: bool = False):
        self.required_role = required_role
        self.optional = optional

    async def __call__(
        self,
        jwt_manager: JWTManagerDep,
        auth_creds: Annotated[HTTPAuthorizationCredentials | None, Depends(user_auth_scheme)] = None,
    ) -> int | None:
        token = auth_creds.credentials if auth_creds else None

        if not token:
            if self.optional:
                return None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = jwt_manager.decode_access_token(token)
            if not payload:
                raise ValueError("Invalid payload")

            user_id = self._extract_user_id(payload)

            if self.required_role is not None:
                user_role = self._extract_user_role(payload)
                self._validate_permissions(user_role)

            return user_id

        except (HTTPException, Exception) as e:
            if self.optional:
                return None

            if isinstance(e, HTTPException):
                raise e

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
            ) from e

    def _extract_user_id(self, payload: dict) -> int:
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token.",
            )
        return int(user_id_str)

    def _extract_user_role(self, payload: dict) -> UserRole:
        role_str = payload.get("role")
        if not role_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role not found in token.",
            )
        try:
            return UserRole(role_str)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unknown role in token.",
            ) from e

    def _validate_permissions(self, user_role: UserRole) -> None:
        if user_role < self.required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions.",
            )
