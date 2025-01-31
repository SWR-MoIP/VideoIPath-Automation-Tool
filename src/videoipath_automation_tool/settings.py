from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for VideoIPath Automation Tool. Used to load and store environment variables."""

    VIPAT_ENVIRONMENT: Optional[str] = Field(default="PROD", env="VIPAT_ENVIRONMENT")  # Literal: "DEV", "TEST", "PROD"
    VIPAT_VIDEOIPATH_IP: Optional[str] = Field(default=None, env="VIPAT_VIDEOIPATH_IP")
    VIPAT_VIDEOIPATH_USER: Optional[str] = Field(default=None, env="VIPAT_VIDEOIPATH_USER")
    VIPAT_VIDEOIPATH_PWD: Optional[str] = Field(default=None, env="VIPAT_VIDEOIPATH_PWD")
    VIPAT_HTTPS: Optional[bool] = Field(default=True, env="VIPAT_HTTPS")
    VIPAT_HTTPS_VERIFY: Optional[bool] = Field(default=True, env="VIPAT_HTTPS_VERIFY")
    VIPAT_LOG_LEVEL: Optional[str] = Field(
        default="INFO", env="VIPAT_LOG_LEVEL"
    )  # Literal: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"

    class Config: 
        env_file = ".env"
        env_file_encoding = "utf-8"
