from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    app_name: str = "WIP Backend"
    debug: bool = True

    # Database
    database_url: str

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # File Upload
    max_file_size: int = 50000000  # 50MB
    allowed_file_types: str = "pdf,PDF"

    # AI Providers (in order of preference)
    # Claude (Anthropic) - Recommended
    anthropic_api_key: Optional[str] = None

    # Runpod - Your alternative
    runpod_endpoint: Optional[str] = None
    runpod_api_key: Optional[str] = None

    # OpenAI - Fallback (rate limited)
    openai_api_key: Optional[str] = None

    # Google Cloud
    google_application_credentials: Optional[str] = None

    # Encryption
    encryption_key: Optional[str] = None
    database_encryption_enabled: bool = True

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set the Google credentials environment variable if provided
        if self.google_application_credentials:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                self.google_application_credentials
            )


settings = Settings()
