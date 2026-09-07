import os
from urllib.parse import quote_plus

import pymysql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from config import Config
from models import Base


def _mysql_server_params():
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "profesor_ia"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
    }


def _mysql_database_name():
    if Config.DATABASE_URL.startswith("mysql"):
        # mysql+pymysql://user:pass@host:port/dbname?charset=utf8mb4
        path = Config.DATABASE_URL.split("?", 1)[0]
        return path.rsplit("/", 1)[-1]
    return os.getenv("MYSQL_DATABASE", "profesor_ia")


def ensure_mysql_database():
    if Config.DB_ENGINE != "mysql":
        return

    params = _mysql_server_params()
    database = _mysql_database_name()

    try:
        conn = pymysql.connect(
            host=params["host"],
            port=params["port"],
            user=params["user"],
            password=params["password"],
            charset="utf8mb4",
        )
    except pymysql.err.OperationalError as exc:
        raise RuntimeError(
            "No se pudo conectar al servidor MySQL. "
            "Verifica que MySQL esté instalado y en ejecución, y revisa MYSQL_* en backend/.env. "
            f"Detalle: {exc}"
        ) from exc

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def _create_engine():
    if Config.DATABASE_URL:
        return create_engine(
            Config.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

    db_path = Config.DATA_DIR / "app.db"
    return create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _ensure_column(table: str, column: str, mysql_ddl: str, sqlite_ddl: str):
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return

    columns = {item["name"] for item in inspector.get_columns(table)}
    if column in columns:
        return

    ddl = mysql_ddl if Config.DB_ENGINE == "mysql" else sqlite_ddl
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _migrate_schema():
    _ensure_column(
        "subjects",
        "llm_model",
        "ALTER TABLE subjects ADD COLUMN llm_model VARCHAR(255) NULL",
        "ALTER TABLE subjects ADD COLUMN llm_model VARCHAR(255)",
    )
    _ensure_column(
        "users",
        "security_question",
        "ALTER TABLE users ADD COLUMN security_question VARCHAR(255) NULL",
        "ALTER TABLE users ADD COLUMN security_question VARCHAR(255)",
    )
    _ensure_column(
        "users",
        "security_answer_hash",
        "ALTER TABLE users ADD COLUMN security_answer_hash VARCHAR(255) NULL",
        "ALTER TABLE users ADD COLUMN security_answer_hash VARCHAR(255)",
    )
    _migrate_subject_teachers()


def _migrate_subject_teachers():
    inspector = inspect(engine)
    if "subject_teachers" not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO subject_teachers (subject_id, teacher_id, is_primary)
                SELECT s.id, s.teacher_id, 1
                FROM subjects s
                WHERE NOT EXISTS (
                    SELECT 1 FROM subject_teachers st
                    WHERE st.subject_id = s.id AND st.teacher_id = s.teacher_id
                )
                """
            )
        )


def init_db():
    if Config.DB_ENGINE == "mysql":
        ensure_mysql_database()
        global engine, SessionLocal
        engine = _create_engine()
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Config.DATA_DIR.mkdir(exist_ok=True)

    try:
        Base.metadata.create_all(bind=engine)
        _migrate_schema()
        if Config.DB_ENGINE == "mysql":
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise RuntimeError(
            "MySQL está configurado pero no se pudieron crear o usar las tablas. "
            "Ejecuta `python setup_mysql.py` desde backend/ o revisa backend/.env. "
            f"Detalle: {exc}"
        ) from exc


def get_session():
    return SessionLocal()


def check_db_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, Config.DB_ENGINE
    except OperationalError as exc:
        return False, str(exc)
