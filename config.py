import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _required_secret_key() -> str:
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY deve ser configurada no ambiente")
    if len(secret_key) < 32 and os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("SECRET_KEY de produção deve ter pelo menos 32 caracteres")
    return secret_key


class Config:
    SECRET_KEY = _required_secret_key()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_REFRESH_EACH_REQUEST = True
    COMMON_SESSION_LIFETIME = timedelta(hours=1)
    ADMIN_SESSION_LIFETIME = timedelta(hours=8)
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE") or None
    QR_RATE_LIMIT = os.environ.get("QR_RATE_LIMIT", "30 per minute")
    QR_RATE_LIMIT_STORAGE_URI = os.environ.get("QR_RATE_LIMIT_STORAGE_URI", "memory://")
