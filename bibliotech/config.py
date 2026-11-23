import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "bibliotech")
    PRAZO_DIAS = int(os.getenv("PRAZO_DIAS", "7"))
    MULTA_POR_DIA = float(os.getenv("MULTA_POR_DIA", "1.00"))
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
