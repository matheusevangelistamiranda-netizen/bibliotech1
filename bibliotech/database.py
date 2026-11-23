from contextlib import contextmanager

import mysql.connector
from flask import current_app


@contextmanager
def conectar():
    conn = mysql.connector.connect(
        host=current_app.config["MYSQL_HOST"],
        port=current_app.config["MYSQL_PORT"],
        user=current_app.config["MYSQL_USER"],
        password=current_app.config["MYSQL_PASSWORD"],
        database=current_app.config["MYSQL_DATABASE"],
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )
    try:
        yield conn
    finally:
        conn.close()
