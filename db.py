import sqlite3
import json

DB_FILE = "pupbot.db"

def _get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    with _get_conn() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)")

def get_val(key, default=None):
    with _get_conn() as conn:
        cursor = conn.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return default

def set_val(key, value):
    with _get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)", (key, json.dumps(value)))
