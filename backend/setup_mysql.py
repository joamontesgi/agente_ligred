#!/usr/bin/env python3
"""Crea la base MySQL y todas las tablas del proyecto."""

from config import Config
from database import check_db_connection, ensure_mysql_database, init_db


def main():
    if Config.DB_ENGINE != "mysql":
        print("MySQL no está configurado.")
        print("Define MYSQL_DATABASE (y credenciales) en backend/.env")
        raise SystemExit(1)

    print(f"Motor: MySQL")
    print(f"URL:   {Config.DATABASE_URL.split('@')[-1]}")

    print("Creando base de datos si no existe...")
    ensure_mysql_database()

    print("Creando tablas...")
    init_db()

    ok, info = check_db_connection()
    if ok:
        print(f"Listo. Conexión OK ({info}).")
    else:
        print(f"Error de conexión: {info}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
