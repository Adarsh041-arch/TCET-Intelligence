from typing import Optional, List, Dict, Any
import sqlite3
import mysql.connector
import psycopg2
from app.core.config import config


class DatabaseConnector:
    def __init__(self):
        self.current_connection = None
        self.db_type = None

    def connect_sqlite(self, db_path: str) -> bool:
        try:
            self.current_connection = sqlite3.connect(db_path)
            self.db_type = "sqlite"
            return True
        except Exception as e:
            print(f"SQLite connection error: {e}")
            return False

    def connect_mysql(
        self, host: str, port: int, user: str, password: str, database: str
    ) -> bool:
        try:
            self.current_connection = mysql.connector.connect(
                host=host, port=port, user=user, password=password, database=database
            )
            self.db_type = "mysql"
            return True
        except Exception as e:
            print(f"MySQL connection error: {e}")
            return False

    def connect_postgresql(
        self, host: str, port: int, user: str, password: str, database: str
    ) -> bool:
        try:
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, database=database
            )
            conn.autocommit = True
            self.current_connection = conn
            self.db_type = "postgresql"
            return True
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")
            return False

    def _reset_connection(self):
        print(f"[_reset_connection] Called. db_type={self.db_type}, conn={self.current_connection is not None}")
        if self.current_connection and self.db_type == "postgresql":
            try:
                if hasattr(self.current_connection, 'autocommit'):
                    self.current_connection.autocommit = True
                self.current_connection.rollback()
                print("[_reset_connection] Rollback successful")
            except Exception as e:
                print(f"[_reset_connection] Rollback failed: {e}")
                pass

    def execute_query(self, query: str) -> Dict[str, Any]:
        if not self.current_connection:
            return {"success": False, "error": "No database connection"}

        self._reset_connection()
        print(f"[execute_query] autocommit={getattr(self.current_connection, 'autocommit', None)}")
        try:
            cursor = self.current_connection.cursor()
            cursor.execute(query)

            if query.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE", "DESC")):
                columns = (
                    [desc[0] for desc in cursor.description]
                    if cursor.description
                    else []
                )
                rows = cursor.fetchall()
                return {
                    "success": True,
                    "type": "select",
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                }
            else:
                self.current_connection.commit()
                return {
                    "success": True,
                    "type": "modify",
                    "affected_rows": cursor.rowcount,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                cursor.close()
            except:
                pass

    def get_tables(self) -> List[str]:
        if not self.current_connection:
            return []

        self._reset_connection()
        if self.db_type == "sqlite":
            cursor = self.current_connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
        elif self.db_type == "mysql":
            cursor = self.current_connection.cursor()
            cursor.execute("SHOW TABLES")
            return [row[0] for row in cursor.fetchall()]
        elif self.db_type == "postgresql":
            import traceback
            try:
                cursor = self.current_connection.cursor()
                cursor.execute("SELECT current_database(), current_user, version()")
                info = cursor.fetchone()
                print(f"[get_tables] DB: {info[0]}, User: {info[1]}, Version: {info[2]}")
                cursor.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')")
                rows = cursor.fetchall()
                print(f"[get_tables] All non-system tables: {rows}")
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
                result = [row[0] for row in cursor.fetchall()]
                print(f"[get_tables] Public tables: {result}")
                return result
            except Exception as e:
                print(f"[get_tables] Error: {e}")
                traceback.print_exc()
                return []

        return []

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        if not self.current_connection:
            return {}

        try:
            cursor = self.current_connection.cursor()

            if self.db_type == "sqlite":
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [
                    {"name": row[1], "type": row[2]} for row in cursor.fetchall()
                ]
            elif self.db_type == "mysql":
                cursor.execute(f"DESCRIBE {table_name}")
                columns = [
                    {"name": row[0], "type": row[1]} for row in cursor.fetchall()
                ]
            elif self.db_type == "postgresql":
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                """)
                columns = [
                    {"name": row[0], "type": row[1]} for row in cursor.fetchall()
                ]

            return {"table": table_name, "columns": columns}
        except Exception as e:
            print(f"Error getting schema: {e}")
            return {}

    def disconnect(self):
        if self.current_connection:
            try:
                self.current_connection.close()
            except:
                pass
            self.current_connection = None
            self.db_type = None

    def connect_from_config(self, config: dict) -> bool:
        db_type = config.get("db_type", "")
        if db_type == "sqlite":
            return self.connect_sqlite(config.get("path", ""))
        elif db_type == "mysql":
            return self.connect_mysql(
                host=config.get("host", "localhost"),
                port=int(config.get("port", 3306)),
                user=config.get("user", "root"),
                password=config.get("password", ""),
                database=config.get("database_name", ""),
            )
        elif db_type == "postgresql":
            return self.connect_postgresql(
                host=config.get("host", "localhost"),
                port=int(config.get("port", 5432)),
                user=config.get("user", "postgres"),
                password=config.get("password", ""),
                database=config.get("database_name", ""),
            )
        return False


db_connector = DatabaseConnector()
