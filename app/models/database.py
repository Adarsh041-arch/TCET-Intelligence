import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from app.core.config import config


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database_url
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_hash TEXT UNIQUE NOT NULL,
                    file_type TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
                )
            """)
            conn.commit()
            self._create_default_admin()

    def _create_default_admin(self):
        from app.core.utils import get_password_hash

        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ?", (config.admin_username,)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (user_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                (
                    "admin-001",
                    config.admin_username,
                    get_password_hash(config.admin_password),
                    "admin",
                ),
            )
            self._get_connection().commit()

    def create_user(
        self, user_id: str, username: str, password: str, role: str
    ) -> bool:
        from app.core.utils import get_password_hash

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (user_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                    (user_id, username, get_password_hash(password), role),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "password_hash": row[2],
                "role": row[3],
                "created_at": row[4],
            }
        return None

    def create_session(
        self, session_id: str, user_id: str, session_name: Optional[str] = None
    ) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sessions (session_id, user_id, session_name) VALUES (?, ?, ?)",
                    (
                        session_id,
                        user_id,
                        session_name
                        or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    ),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT session_id, session_name, created_at, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
        return [
            {
                "session_id": row[0],
                "session_name": row[1],
                "created_at": row[2],
                "updated_at": row[3],
            }
            for row in cursor.fetchall()
        ]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return {
                "session_id": row[0],
                "user_id": row[1],
                "session_name": row[2],
                "created_at": row[3],
                "updated_at": row[4],
            }
        return None

    def add_message(self, session_id: str, role: str, content: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            message_id = cursor.lastrowid or 0
            cursor.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
        return message_id

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT message_id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        return [
            {
                "message_id": row[0],
                "role": row[1],
                "content": row[2],
                "created_at": row[3],
            }
            for row in cursor.fetchall()
        ]

    def save_document(
        self,
        doc_id: str,
        filename: str,
        file_hash: str,
        file_type: str,
        uploaded_by: str,
    ) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO documents (doc_id, filename, file_hash, file_type, uploaded_by) VALUES (?, ?, ?, ?, ?)",
                    (doc_id, filename, file_hash, file_type, uploaded_by),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_document_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))
        row = cursor.fetchone()
        if row:
            return {
                "doc_id": row[0],
                "filename": row[1],
                "file_hash": row[2],
                "file_type": row[3],
                "uploaded_by": row[4],
                "uploaded_at": row[5],
            }
        return None

    def get_all_documents(self) -> List[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT doc_id, filename, file_type, uploaded_by, uploaded_at FROM documents ORDER BY uploaded_at DESC"
        )
        return [
            {
                "doc_id": row[0],
                "filename": row[1],
                "file_type": row[2],
                "uploaded_by": row[3],
                "uploaded_at": row[4],
            }
            for row in cursor.fetchall()
        ]

    def delete_document(self, doc_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0


db = Database()
