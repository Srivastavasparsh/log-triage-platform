import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "telemetry.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            log_level TEXT,
            service_name TEXT,
            message TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS remediations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            service_name TEXT,
            file_path TEXT,
            error_type TEXT,
            root_cause TEXT,
            status TEXT,
            pr_url TEXT
        )
    """)
    conn.commit()
    conn.close()


def insert_log(level: str, service: str, message: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (log_level, service_name, message) VALUES (?, ?, ?)",
        (level, service, message),
    )
    conn.commit()
    conn.close()


def insert_remediation(
    service: str,
    file_path: str,
    error_type: str,
    root_cause: str,
    status: str,
    pr_url: str = "",
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO remediations (service_name, file_path, error_type, root_cause, status, pr_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (service, file_path, error_type, root_cause, status, pr_url),
    )
    conn.commit()
    conn.close()