from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://postgres:2182004nam@localhost:5432/babycare"
    
    # JWT Authentication
    jwt_secret: str = "supersecretkey"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application
    app_name: str = "Baby Health Monitoring API"
    debug: bool = True
    
    # File Upload
    upload_dir: str = "uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    
    # AI Model - renamed to avoid Pydantic conflict
    cry_model_path: str = "models/best.pt"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        protected_namespaces = ('settings_',)  # Fix the warning


settings = Settings()