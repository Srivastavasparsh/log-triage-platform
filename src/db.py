import sqlite3
import os

# Set absolute path to telemetry.db in the root project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "telemetry.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            log_level TEXT,
            service_name TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_log(level, service, message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (log_level, service_name, message) VALUES (?, ?, ?)",
        (level, service, message)
    )
    conn.commit()
    conn.close()