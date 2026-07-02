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
            self.current_connection = psycopg2.connect(
                host=host, port=port, user=user, password=password, database=database
            )
            self.db_type = "postgresql"
            return True
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")
            return False

    def execute_query(self, query: str) -> Dict[str, Any]:
        if not self.current_connection:
            return {"success": False, "error": "No database connection"}

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

        try:
            if self.db_type == "sqlite":
                cursor = self.current_connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                return [row[0] for row in cursor.fetchall()]
            elif self.db_type == "mysql":
                cursor = self.current_connection.cursor()
                cursor.execute("SHOW TABLES")
                return [row[0] for row in cursor.fetchall()]
            elif self.db_type == "postgresql":
                cursor = self.current_connection.cursor()
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting tables: {e}")
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


db_connector = DatabaseConnector()
