from functools import lru_cache
from typing import Optional

from pydantic import RedisDsn
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    testing: bool = False
    sql_logs: bool = False

    db_user: str = "user"
    db_password: Optional[str] = None
    db_name: str = "database"
    db_host: str = "localhost"
    db_port: str = "5432"
    db_driver: str = "asyncpg"
    db: str = "postgresql"
    db_pool_size: Optional[int] = 50
    db_max_overflow: Optional[int] = 25
    db_pool_timeout: Optional[int] = 30

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_user: Optional[str] = None
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_pool_size: Optional[int] = 50

    kafka_host: str = "localhost"
    kafka_port: int = 9092

    jwt_secret_key: str = "<KEY>"
    jwt_algorithm: str = "HS256"
    jwt_expires_in: int = 3600

    password_algorithm: str = "sha256"
    password_iterations: int = 600000

    enable_metrics: bool = False
    metrics_token: str = "<METRICS_TOKEN>"

    mail_username: Optional[str] = None
    mail_password: Optional[str] = None
    mail_from: Optional[str] = None
    mail_server: Optional[str] = None
    mail_port: Optional[int] = None
    mail_starttls: Optional[bool] = None
    mail_ssl_tls: Optional[bool] = None
    mail_use_credentials: Optional[bool] = None
    mail_validate_certs: Optional[bool] = None

    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    payment_gateway_mock_mode: bool = True

    @property
    def kafka_url(self) -> str:
        return f"{self.kafka_host}:{self.kafka_port}"

    @property
    def redis_url(self) -> str:
        dsn = RedisDsn.build(
            scheme="redis",
            username=self.redis_user,
            password=self.redis_password,
            host=self.redis_host,
            port=self.redis_port,
            path=f"/{self.redis_db}",
        )
        return str(dsn)

    @property
    def db_url(self) -> str:
        auth = f"{self.db_user}"
        if self.db_password:
            auth += f":{self.db_password}"

        return f"{self.db}+{self.db_driver}://{auth}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache
def get_settings() -> AppConfig:
    return AppConfig()

