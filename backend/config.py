import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")


def _build_mysql_url():
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "profesor_ia")
    password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    database = os.getenv("MYSQL_DATABASE", "profesor_ia")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


class Config:
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    _cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
    CORS_ORIGINS = (
        "*"
        if _cors_raw == "*"
        else [o.strip() for o in _cors_raw.split(",") if o.strip()]
    )
    DATA_DIR = ROOT_DIR / "data"
    CHROMA_DIR = ROOT_DIR / "chroma"
    DOCUMENTOS_DIR = ROOT_DIR / "documentos"

    DATABASE_URL = os.getenv("DATABASE_URL") or (
        _build_mysql_url() if os.getenv("MYSQL_DATABASE") else ""
    )
    DB_ENGINE = "mysql" if DATABASE_URL.startswith("mysql") else "sqlite"

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "qwen2.5:7b")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
