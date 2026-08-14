"""
Central configuration. Reads DB credentials from a .env file so nothing
sensitive gets committed to git. Copy .env.example -> .env and fill in
your local MySQL password before running any script.
"""
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "consultbae"),
}