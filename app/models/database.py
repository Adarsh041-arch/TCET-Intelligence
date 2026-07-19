import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from app.core.config import config

try:
    import psycopg2
    DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg2.IntegrityError)
except ImportError:
    DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,)


class SafeConnection:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres

    def cursor(self):
        return SafeCursor(self.conn.cursor(), self, self.is_postgres)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                self.conn.rollback()
            except Exception:
                pass
        else:
            try:
                self.conn.commit()
            except Exception:
                pass
        try:
            self.conn.close()
        except Exception:
            pass

    def __del__(self):
        try:
            self.conn.commit()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass


class SafeCursor:
    def __init__(self, cursor, conn_wrapper, is_postgres=False):
        self.cursor = cursor
        self.conn_wrapper = conn_wrapper
        self.is_postgres = is_postgres

    def execute(self, sql, params=None):
        if self.is_postgres:
            sql = sql.replace("?", "%s")
            if "INSERT OR REPLACE INTO user_api_keys" in sql:
                sql = "INSERT INTO user_api_keys (user_id, provider, api_key) VALUES (%s, %s, %s) ON CONFLICT (user_id, provider) DO UPDATE SET api_key = EXCLUDED.api_key"
            elif "INSERT OR IGNORE INTO user_allowed_directories" in sql:
                sql = "INSERT INTO user_allowed_directories (user_id, directory_path) VALUES (%s, %s) ON CONFLICT (user_id, directory_path) DO NOTHING"
            
            sql = sql.replace("INSERT OR IGNORE", "INSERT")
            sql = sql.replace("INSERT OR REPLACE", "INSERT")
        
        if params is not None:
            self.cursor.execute(sql, params)
        else:
            self.cursor.execute(sql)
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def lastrowid(self):
        try:
            return self.cursor.lastrowid
        except Exception:
            return 0
    
    @property
    def rowcount(self):
        return self.cursor.rowcount


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_url = db_path or config.database_url
        self.is_postgres = self.db_url.startswith("postgresql://") or self.db_url.startswith("postgres://")
        if not self.is_postgres:
            Path(self.db_url).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        if self.is_postgres:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            return SafeConnection(conn, is_postgres=True)
        else:
            conn = sqlite3.connect(self.db_url)
            return SafeConnection(conn, is_postgres=False)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            def run_create(sql):
                if self.is_postgres:
                    sql = sql.replace("AUTOINCREMENT", "")
                    sql = sql.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")
                cursor.execute(sql)

            run_create("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            run_create("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            run_create("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            run_create("""
                CREATE TABLE IF NOT EXISTS user_api_keys (
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'tavily',
                    api_key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, provider),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            run_create("""
                CREATE TABLE IF NOT EXISTS user_allowed_directories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    directory_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, directory_path)
                )
            """)
            run_create("""
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
            run_create("""
                CREATE TABLE IF NOT EXISTS tcet_doc_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    file_hash TEXT,
                    file_size INTEGER,
                    indexed INTEGER DEFAULT 0,
                    doc_id TEXT,
                    chunks_count INTEGER DEFAULT 0,
                    indexed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            run_create("""
                CREATE TABLE IF NOT EXISTS exposed_databases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    db_type TEXT NOT NULL,
                    host TEXT,
                    port INTEGER,
                    db_user TEXT,
                    password TEXT,
                    database_name TEXT,
                    path TEXT,
                    label TEXT NOT NULL,
                    exposed_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (exposed_by) REFERENCES users(user_id)
                )
            """)
            conn.commit()
            self._create_default_admin()

    def _create_default_admin(self):
        from app.core.utils import get_password_hash

        with self._get_connection() as conn:
            cursor = conn.cursor()
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
                conn.commit()

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
        except DB_INTEGRITY_ERRORS:
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
        except DB_INTEGRITY_ERRORS:
            return False

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            """
            SELECT s.session_id, s.session_name, s.created_at, s.updated_at,
                   (SELECT m.content FROM messages m WHERE m.session_id = s.session_id AND m.role = 'user' ORDER BY m.message_id ASC LIMIT 1) AS first_message
            FROM sessions s WHERE s.user_id = ? ORDER BY s.updated_at DESC
            """,
            (user_id,),
        )
        return [
            {
                "session_id": row[0],
                "session_name": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "first_message": row[4] or "",
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

    def delete_session(self, session_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False

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
        except DB_INTEGRITY_ERRORS:
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

    def get_document_by_filename(self, filename: str, user_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT doc_id, filename, file_hash, file_type, uploaded_by, uploaded_at FROM documents WHERE filename = ? AND uploaded_by = ? ORDER BY uploaded_at DESC LIMIT 1",
            (filename, user_id),
        )
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

    def set_api_key(self, user_id: str, provider: str, api_key: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO user_api_keys (user_id, provider, api_key) VALUES (?, ?, ?)",
                    (user_id, provider, api_key),
                )
                conn.commit()
            return True
        except Exception:
            return False

    def get_api_key(self, user_id: str, provider: str = "tavily") -> Optional[str]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT api_key FROM user_api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def delete_api_key(self, user_id: str, provider: str = "tavily") -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_api_keys WHERE user_id = ? AND provider = ?",
                (user_id, provider),
            )
            conn.commit()
            return cursor.rowcount > 0

    # ── User Allowed Directories ──────────────────────────────
    def add_user_directory(self, user_id: str, directory_path: str) -> bool:
        try:
            normalized = os.path.normpath(directory_path)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO user_allowed_directories (user_id, directory_path) VALUES (?, ?)",
                    (user_id, normalized),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_user_directories(self, user_id: str) -> List[str]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT directory_path FROM user_allowed_directories WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        return [row[0] for row in cursor.fetchall()]

    def delete_user_directory(self, user_id: str, directory_path: str) -> bool:
        try:
            normalized = os.path.normpath(directory_path)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM user_allowed_directories WHERE user_id = ? AND directory_path = ?",
                    (user_id, normalized),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_user_directory_list(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT id, directory_path, created_at FROM user_allowed_directories WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        return [
            {"id": row[0], "directory_path": row[1], "created_at": row[2]}
            for row in cursor.fetchall()
        ]


    # ── Exposed Databases ──────────────────────────────────
    def expose_database(self, db_config: dict, exposed_by: str) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                sql = """INSERT INTO exposed_databases (db_type, host, port, db_user, password, database_name, path, label, exposed_by)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                if self.is_postgres:
                    sql += " RETURNING id"
                cursor.execute(
                    sql,
                    (
                        db_config["db_type"],
                        db_config.get("host", ""),
                        db_config.get("port", 0),
                        db_config.get("db_user", db_config.get("user", "")),
                        db_config.get("password", ""),
                        db_config.get("database_name", ""),
                        db_config.get("path", ""),
                        db_config["label"],
                        exposed_by,
                    ),
                )
                if self.is_postgres:
                    row = cursor.fetchone()
                    db_id = row[0] if row else 0
                else:
                    db_id = cursor.lastrowid or 0
                conn.commit()
                return db_id
        except Exception as e:
            print(f"Error exposing database: {e}")
            return 0

    def get_exposed_databases(self) -> List[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT id, db_type, host, port, database_name, path, label, exposed_by, created_at FROM exposed_databases ORDER BY created_at DESC"
        )
        return [
            {
                "id": row[0],
                "db_type": row[1],
                "host": row[2],
                "port": row[3],
                "database_name": row[4],
                "path": row[5],
                "label": row[6],
                "exposed_by": row[7],
                "created_at": row[8],
            }
            for row in cursor.fetchall()
        ]

    def get_exposed_database(self, db_id: int) -> Optional[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT id, db_type, host, port, db_user, password, database_name, path, label, exposed_by, created_at FROM exposed_databases WHERE id = ?",
            (db_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "db_type": row[1],
                "host": row[2],
                "port": row[3],
                "user": row[4],
                "password": row[5],
                "database_name": row[6],
                "path": row[7],
                "label": row[8],
                "exposed_by": row[9],
                "created_at": row[10],
            }
        return None

    def delete_exposed_database(self, db_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM exposed_databases WHERE id = ?", (db_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting exposed database: {e}")
            return False

    # ── TCET Documents Index Management ────────────────────
    def get_tcet_doc_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT * FROM tcet_doc_index WHERE file_path = ?", (file_path,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "file_name": row[1],
                "file_path": row[2],
                "file_hash": row[3],
                "file_size": row[4],
                "indexed": bool(row[5]),
                "doc_id": row[6],
                "chunks_count": row[7],
                "indexed_at": row[8],
                "created_at": row[9],
            }
        return None

    def upsert_tcet_doc(self, file_name: str, file_path: str, file_hash: str, file_size: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO tcet_doc_index (file_name, file_path, file_hash, file_size)
                       VALUES (?, ?, ?, ?)
                        ON CONFLICT(file_path) DO UPDATE SET
                          file_name = excluded.file_name,
                          file_hash = excluded.file_hash,
                          file_size = excluded.file_size,
                          indexed = CASE WHEN tcet_doc_index.indexed = 1 AND excluded.file_hash != tcet_doc_index.file_hash THEN 0 ELSE tcet_doc_index.indexed END,
                          doc_id = CASE WHEN excluded.file_hash != tcet_doc_index.file_hash THEN NULL ELSE tcet_doc_index.doc_id END,
                          chunks_count = CASE WHEN excluded.file_hash != tcet_doc_index.file_hash THEN 0 ELSE tcet_doc_index.chunks_count END,
                          indexed_at = CASE WHEN excluded.file_hash != tcet_doc_index.file_hash THEN NULL ELSE tcet_doc_index.indexed_at END""",
                    (file_name, file_path, file_hash, file_size),
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"Error upserting tcet doc: {e}")
            return False

    def mark_tcet_doc_indexed(self, file_path: str, doc_id: str, chunks_count: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE tcet_doc_index
                       SET indexed = 1, doc_id = ?, chunks_count = ?, indexed_at = CURRENT_TIMESTAMP
                       WHERE file_path = ?""",
                    (doc_id, chunks_count, file_path),
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"Error marking tcet doc indexed: {e}")
            return False

    def get_all_tcet_docs(self) -> List[Dict[str, Any]]:
        cursor = self._get_connection().cursor()
        cursor.execute(
            "SELECT * FROM tcet_doc_index ORDER BY file_name ASC"
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "file_name": row[1],
                "file_path": row[2],
                "file_hash": row[3],
                "file_size": row[4],
                "indexed": bool(row[5]),
                "doc_id": row[6],
                "chunks_count": row[7],
                "indexed_at": row[8],
                "created_at": row[9],
            })
        return result

    def delete_tcet_doc(self, file_path: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tcet_doc_index WHERE file_path = ?", (file_path,))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting tcet doc record: {e}")
            return False


db = Database()
