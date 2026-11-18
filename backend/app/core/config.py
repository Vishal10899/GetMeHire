import os
from typing import List, Optional, Union, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "GetMeHire"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-production-key-change-in-env-987462810")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # PostgreSQL Configuration
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "127.0.0.1")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "123456")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "job_discovery")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    
    DATABASE_URL: Optional[str] = None

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    BACKEND_CORS_ORIGIN_REGEX: Optional[str] = os.getenv(
        "BACKEND_CORS_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            import json
            return json.loads(v)
        return v

    # Resume upload storage (PRD 9.2: pluggable local or S3-compatible cloud object storage)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")  # local, s3
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "storage", "resumes"))
    MAX_RESUME_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    ALLOWED_RESUME_TYPES: List[str] = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]

    # S3 / Cloudflare R2 / MinIO storage configuration
    S3_BUCKET_NAME: Optional[str] = os.getenv("S3_BUCKET_NAME", None)
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL", None)  # e.g., Cloudflare R2 or MinIO
    S3_REGION_NAME: str = os.getenv("S3_REGION_NAME", "us-east-1")
    S3_ACCESS_KEY_ID: Optional[str] = os.getenv("S3_ACCESS_KEY_ID", None)
    S3_SECRET_ACCESS_KEY: Optional[str] = os.getenv("S3_SECRET_ACCESS_KEY", None)
    S3_FORCE_PATH_STYLE: bool = True  # Required for MinIO

    # Background Ingestion Scheduler (PRD §5.4 & §10.2)
    ENABLE_BACKGROUND_SCHEDULER: bool = False
    SCHEDULER_INTERVAL_SECONDS: int = 300

    # Official USAJobs API Integration (Optional/Configurable)
    USAJOBS_API_KEY: Optional[str] = os.getenv("USAJOBS_API_KEY", None)
    USAJOBS_USER_AGENT_EMAIL: Optional[str] = os.getenv("USAJOBS_USER_AGENT_EMAIL", None)

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

    def model_post_init(self, __context: Any) -> None:
        # Enforce strict production secret validation
        if self.ENVIRONMENT.lower() == "production":
            if (
                not self.SECRET_KEY
                or len(self.SECRET_KEY) < 32
                or any(k in self.SECRET_KEY.lower() for k in ["super-secret", "change-in-env", "generate-a-strong"])
            ):
                raise ValueError("CRITICAL SECURITY VIOLATION: Production requires a secure SECRET_KEY (minimum 32 characters, non-default).")
            if self.POSTGRES_PASSWORD == "123456":
                raise ValueError("CRITICAL SECURITY VIOLATION: Production requires a secure, non-default POSTGRES_PASSWORD.")
            if self.STORAGE_BACKEND == "s3" and not self.S3_BUCKET_NAME:
                raise ValueError("CRITICAL CONFIGURATION ERROR: Production S3 storage requires S3_BUCKET_NAME to be configured.")

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
