"""Opens a connection to the Soufflé SQLite database."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "souffle.db"


def get_connection(path=DB_PATH):
    """Return a connection with foreign keys enforced and rows readable by column name."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
