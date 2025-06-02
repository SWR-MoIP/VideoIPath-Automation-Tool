from typing import Annotated, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for VideoIPath Automation Tool. Used to load and store environment variables."""

    VIPAT_ENVIRONMENT: Literal["DEV", "PROD"] = Field(default="PROD")
    VIPAT_VIDEOIPATH_SERVER_ADDRESS: Annotated[str | None, Field()] = None
    VIPAT_VIDEOIPATH_USERNAME: Annotated[str | None, Field()] = None
    VIPAT_VIDEOIPATH_PASSWORD: Annotated[str | None, Field()] = None
    VIPAT_USE_HTTPS: bool = Field(default=True)
    VIPAT_VERIFY_SSL_CERT: bool = Field(default=True)
    VIPAT_LOG_LEVEL: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None
    VIPAT_ADVANCED_DRIVER_SCHEMA_CHECK: bool = Field(default=True)
    VIPAT_TIMEOUT_HTTP_GET: int = Field(default=10)
    VIPAT_TIMEOUT_HTTP_PATCH: int = Field(default=10)
    VIPAT_TIMEOUT_HTTP_POST: int = Field(default=10)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # User should be able to add extra environment variables for their own use
