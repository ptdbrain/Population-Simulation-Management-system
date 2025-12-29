from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+aiomysql://root:@localhost/residence_db"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Registration verification codes
    ADMIN_REGISTER_CODE: str = "ADMIN2024"
    LEADER_REGISTER_CODE: str = "LEADER2024"

    class Config:
        env_file = ".env"

settings = Settings()
