"""Database abstraction layer supporting SQLite and PostgreSQL."""

import os
import sqlite3
import threading
from typing import Union, Optional, Any, Dict, List
from contextlib import contextmanager
from urllib.parse import urlparse

# Try to import psycopg2, but don't fail if it's not available
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False


class DatabaseAdapter:
    """Abstract base class for database adapters."""
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        raise NotImplementedError
    
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        raise NotImplementedError
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
    
    def fetchall(self) -> List[Dict[str, Any]]:
        raise NotImplementedError
    
    def commit(self):
        raise NotImplementedError
    
    def rollback(self):
        raise NotImplementedError
    
    def close(self):
        raise NotImplementedError
    
    @property
    def lastrowid(self) -> Optional[int]:
        raise NotImplementedError


class SQLiteAdapter(DatabaseAdapter):
    """SQLite adapter using thread-local connections."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA foreign_keys = ON")
        return self._local.conn
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        conn = self._get_conn()
        if params:
            self._local.cursor = conn.execute(query, params)
        else:
            self._local.cursor = conn.execute(query)
        return self._local.cursor
    
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        conn = self._get_conn()
        self._local.cursor = conn.executemany(query, params_list)
        return self._local.cursor
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        if hasattr(self._local, 'cursor'):
            row = self._local.cursor.fetchone()
            return dict(row) if row else None
        return None
    
    def fetchall(self) -> List[Dict[str, Any]]:
        if hasattr(self._local, 'cursor'):
            return [dict(row) for row in self._local.cursor.fetchall()]
        return []
    
    def commit(self):
        self._get_conn().commit()
    
    def rollback(self):
        self._get_conn().rollback()
    
    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    @property
    def lastrowid(self) -> Optional[int]:
        if hasattr(self._local, 'cursor'):
            return self._local.cursor.lastrowid
        return None


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL adapter using psycopg2."""
    
    def __init__(self, connection_string: str):
        if not HAS_POSTGRES:
            raise ImportError("psycopg2 is required for PostgreSQL support. Install with: pip install psycopg2-binary")
        
        self.connection_string = connection_string
        self._conn = None
        self._cursor = None
        self._lastrowid = None
    
    def _get_conn(self):
        """Get or create connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.connection_string)
        return self._conn
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        conn = self._get_conn()
        self._cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Convert SQLite placeholders to PostgreSQL style
            if params:
                query = self._convert_placeholders(query)
            
            # Handle RETURNING for INSERT statements
            if query.strip().upper().startswith('INSERT') and 'RETURNING' not in query.upper():
                query = query.rstrip(';') + ' RETURNING id;'
            
            self._cursor.execute(query, params)
            
            # Capture lastrowid for INSERT statements
            if query.strip().upper().startswith('INSERT'):
                result = self._cursor.fetchone()
                if result and 'id' in result:
                    self._lastrowid = result['id']
            
            return self._cursor
        except Exception as e:
            conn.rollback()
            raise e
    
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        conn = self._get_conn()
        self._cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = self._convert_placeholders(query)
        self._cursor.executemany(query, params_list)
        return self._cursor
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        if self._cursor:
            result = self._cursor.fetchone()
            return dict(result) if result else None
        return None
    
    def fetchall(self) -> List[Dict[str, Any]]:
        if self._cursor:
            return [dict(row) for row in self._cursor.fetchall()]
        return []
    
    def commit(self):
        if self._conn:
            self._conn.commit()
    
    def rollback(self):
        if self._conn:
            self._conn.rollback()
    
    def close(self):
        if self._cursor:
            self._cursor.close()
        if self._conn:
            self._conn.close()
    
    @property
    def lastrowid(self) -> Optional[int]:
        return self._lastrowid
    
    @staticmethod
    def _convert_placeholders(query: str) -> str:
        """Convert SQLite ? placeholders to PostgreSQL %s placeholders."""
        return query.replace('?', '%s')


class Database:
    """Database connection manager that supports both SQLite and PostgreSQL."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            connection_string: Either a path to SQLite file or PostgreSQL connection string.
                             If not provided, uses DATABASE_URL or BOARD_DB_PATH from environment.
        """
        if connection_string is None:
            # Check for PostgreSQL URL first
            connection_string = os.environ.get('DATABASE_URL')
            if not connection_string:
                # Fall back to SQLite
                db_path = os.environ.get('BOARD_DB_PATH', 'board.db')
                connection_string = f"sqlite:///{db_path}"
        
        self.connection_string = connection_string
        self.adapter = self._create_adapter(connection_string)
    
    def _create_adapter(self, connection_string: str) -> DatabaseAdapter:
        """Create appropriate database adapter based on connection string."""
        if connection_string.startswith('sqlite://'):
            # Extract path from sqlite:///path/to/db
            db_path = connection_string[10:]  # Remove 'sqlite:///'
            return SQLiteAdapter(db_path)
        elif connection_string.startswith('postgresql://') or connection_string.startswith('postgres://'):
            return PostgreSQLAdapter(connection_string)
        else:
            # Assume it's a file path for SQLite
            return SQLiteAdapter(connection_string)
    
    def execute(self, query: str, params: Optional[tuple] = None) -> DatabaseAdapter:
        """Execute a query and return the adapter for further operations."""
        self.adapter.execute(query, params)
        return self.adapter
    
    def executemany(self, query: str, params_list: List[tuple]) -> DatabaseAdapter:
        """Execute a query with multiple parameter sets."""
        self.adapter.executemany(query, params_list)
        return self.adapter
    
    def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Execute a query and fetch one row."""
        try:
            self.execute(query, params)
            return self.adapter.fetchone()
        except Exception as e:
            self.rollback()
            raise e
    
    def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and fetch all rows."""
        try:
            self.execute(query, params)
            return self.adapter.fetchall()
        except Exception as e:
            self.rollback()
            raise e
    
    def commit(self):
        """Commit the current transaction."""
        self.adapter.commit()
    
    def rollback(self):
        """Rollback the current transaction."""
        self.adapter.rollback()
    
    def close(self):
        """Close the database connection."""
        self.adapter.close()
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get or create global database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db


def init_db(connection_string: Optional[str] = None):
    """Initialize database with specific connection string."""
    global _db
    _db = Database(connection_string)
    return _db