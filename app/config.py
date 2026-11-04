import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from cryptography.fernet import Fernet


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Identidade e Aplicação
    APP_NAME: str = "Focus Publisher"
    APP_ENV: str = "development"
    DEBUG: bool = False
    APP_SECRET: str = "focus-publisher-insecure-secret-key-change-in-production"
    
    # Chave Fernet (32 bytes url-safe base64). Se vazia ou padrão em dev, geramos uma determinística/fallback.
    TOKEN_ENCRYPTION_KEY: str = Field(
        default_factory=lambda: Fernet.generate_key().decode()
    )

    # Modo de Operação
    # Opções: DEMO, DIRECT_POST, MANUAL_STUDIO, UPLOAD
    OPERATION_MODE: str = "DEMO"

    # Fuso Horário de Operação
    TIMEZONE: str = "America/Fortaleza"

    # Calendário e Meta Diária
    DAILY_POST_TARGET: int = 10
    POST_SLOTS: List[str] = [
        "08:00", "09:30", "11:00", "12:30", "14:00",
        "15:30", "17:00", "18:30", "20:00", "21:30"
    ]
    MAX_CALENDAR_DAYS: int = 30
    OVERDUE_TOLERANCE_MINUTES: int = 15  # Tolerância antes de marcar como atrasado/reagendar

    # Banco de Dados e Cache / Broker
    DATABASE_URL: str = Field(
        default_factory=lambda: (
            "sqlite:////tmp/focus_publisher.db"
            if (os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(".", os.W_OK))
            else "sqlite:///./focus_publisher.db"
        )
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    # Google Drive
    GOOGLE_DRIVE_FOLDER_ID: str = "sample_drive_folder_id"
    DRIVE_INCLUDE_SUBFOLDERS: bool = False
    DRIVE_SYNC_INTERVAL_MINUTES: int = 15
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/connections/google/callback"
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""

    # TikTok
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_REDIRECT_URI: str = "http://localhost:8000/connections/tiktok/callback"

    # IA Opcional para Legendas (Desativada por padrão)
    AI_CAPTION_ENABLED: bool = False
    AI_PROVIDER: str = "mock"  # mock, openai, gemini
    AI_API_KEY: str = ""

    # Armazenamento e Limites
    STORAGE_DIR: str = Field(
        default_factory=lambda: (
            "/tmp/storage"
            if (os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(".", os.W_OK))
            else "./storage"
        )
    )
    MAX_FILE_SIZE_BYTES: int = 1024 * 1024 * 500  # 500 MB
    TEMP_CLEANUP_DAYS: int = 7

    # Autenticação Administrativa Simples
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = "$2b$12$e80yq9g6.w960b7iC47lke9Zf0.5dG7s4mRz7b4q0bX4kE9qU4b5q"  # admin


settings = Settings()

# Cria pastas de armazenamento apenas se o sistema permitir escrita (evita erro em ambientes read-only como Vercel)
try:
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "media"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "thumbnails"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "exports"), exist_ok=True)
except Exception:
    pass
