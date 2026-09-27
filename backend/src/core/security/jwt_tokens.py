from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt


class JWTManager:
    def __init__(self, secret_key: str, algorithm: str, expire_seconds: int):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_seconds = expire_seconds

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(seconds=self.expire_seconds)

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_access_token(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.PyJWTError:
            return None
