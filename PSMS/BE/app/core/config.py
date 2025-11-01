# app/core/config.py
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://root:ptd20092005@localhost:3306/db"
    SECRET_KEY: str = "supersecretkey"  # đổi khóa này khi triển khai thật
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 ngày

settings = Settings()
