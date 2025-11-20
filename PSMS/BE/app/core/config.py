import json
from pathlib import Path
from typing import Dict, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_FRONTEND_DIST = (_REPO_ROOT / "FE" / "publics").resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "sqlite:///./psms.db"
    SECRET_KEY: str = "change-me"  # override bằng biến môi trường
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 giờ
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "null",  # hỗ trợ chạy file://
    ]
    FRONTEND_DIST_PATH: Path | None = _DEFAULT_FRONTEND_DIST if _DEFAULT_FRONTEND_DIST.exists() else None
    ROLE_REGISTRATION_SECRETS: Dict[str, str] = {}
    AUTO_CREATE_SCHEMA: bool = True
    ADMIN_REGISTRATION_CODE: str = "admin-invite"
    MANAGER_REGISTRATION_CODE: str = "manager-invite"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("FRONTEND_DIST_PATH", mode="before")
    @classmethod
    def convert_path(cls, value):
        if not value:
            return _DEFAULT_FRONTEND_DIST if _DEFAULT_FRONTEND_DIST.exists() else None
        resolved = Path(value).resolve()
        return resolved if resolved.exists() else None

    @field_validator("ROLE_REGISTRATION_SECRETS", mode="before")
    @classmethod
    def parse_role_secrets(cls, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
            # support format admin:code;leader:code
            pairs = [item.strip() for item in value.split(",") if item.strip()]
            secrets = {}
            for pair in pairs:
                if ":" in pair:
                    role, secret = pair.split(":", 1)
                    secrets[role.strip()] = secret.strip()
            return secrets
        return value or {}


settings = Settings()
# app/core/config.py
