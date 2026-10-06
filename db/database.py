import sqlite3
from config import SQLITE_CONNECTION_PATH
def get_connection(path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
def create_table(path):
    connection=get_connection(path)
    
    cursor=connection.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS sets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
            )
    """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (set_id) REFERENCES sets(id)
            )
    """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            chunk_count INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (set_id) REFERENCES sets(id)
            )
    """)

    connection.commit()
