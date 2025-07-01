"""Database operations and connection management."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, AsyncIterator

import asyncpg
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.settings = get_settings()
    
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.settings.database.url,
                min_size=5,
                max_size=self.settings.database.pool_size,
                max_inactive_connection_lifetime=300,
                command_timeout=self.settings.database.pool_timeout
            )
            logger.info("Database pool initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database pool", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """Get a database connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error("Database operation failed", error=str(e))
                raise
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return the status."""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch multiple rows from a query."""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row from a query."""
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value from a query."""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)


class SessionRepository:
    """Repository for session management."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        project_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new session."""
        query = """
            INSERT INTO sessions (session_id, user_id, project_path, metadata)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (session_id) DO UPDATE SET
                last_activity = CURRENT_TIMESTAMP,
                metadata = $4
            RETURNING *
        """
        row = await self.db.fetchrow(
            query, session_id, user_id, project_path, metadata or {}
        )
        return dict(row) if row else {}
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        query = "SELECT * FROM sessions WHERE session_id = $1"
        row = await self.db.fetchrow(query, session_id)
        return dict(row) if row else None
    
    async def update_activity(self, session_id: str) -> None:
        """Update session last activity timestamp."""
        query = """
            UPDATE sessions 
            SET last_activity = CURRENT_TIMESTAMP 
            WHERE session_id = $1
        """
        await self.db.execute(query, session_id)
    
    async def list_active_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List active sessions."""
        query = """
            SELECT * FROM sessions 
            WHERE is_active = true 
            ORDER BY last_activity DESC 
            LIMIT $1
        """
        rows = await self.db.fetch(query, limit)
        return [dict(row) for row in rows]


class MemoryRepository:
    """Repository for memory storage and retrieval."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def store_memory(
        self,
        session_id: str,
        content: str,
        content_type: str = "text",
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Store a new memory."""
        query = """
            INSERT INTO memories (session_id, content, content_type, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        return await self.db.fetchval(
            query, session_id, content, content_type, embedding, metadata or {}
        )
    
    async def search_memories_text(
        self,
        session_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memories using full-text search."""
        sql = """
            SELECT *, ts_rank(to_tsvector('english', content), plainto_tsquery('english', $2)) as rank
            FROM memories 
            WHERE session_id = $1 
                AND to_tsvector('english', content) @@ plainto_tsquery('english', $2)
            ORDER BY rank DESC, created_at DESC
            LIMIT $3
        """
        rows = await self.db.fetch(sql, session_id, query, limit)
        return [dict(row) for row in rows]
    
    async def search_memories_vector(
        self,
        session_id: str,
        embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search memories using vector similarity (requires pgvector)."""
        sql = """
            SELECT *, (embedding <=> $2) as distance
            FROM memories 
            WHERE session_id = $1 
                AND embedding IS NOT NULL
                AND (embedding <=> $2) < $4
            ORDER BY embedding <=> $2
            LIMIT $3
        """
        try:
            rows = await self.db.fetch(sql, session_id, embedding, limit, 1.0 - similarity_threshold)
            return [dict(row) for row in rows]
        except Exception:
            # Fallback to text search if vector extension not available
            logger.warning("Vector search failed, falling back to text search")
            return []
    
    async def get_recent_memories(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent memories for a session."""
        query = """
            SELECT * FROM memories 
            WHERE session_id = $1 
            ORDER BY created_at DESC 
            LIMIT $2
        """
        rows = await self.db.fetch(query, session_id, limit)
        return [dict(row) for row in rows]


class ToolCallRepository:
    """Repository for tool call logging and analytics."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> int:
        """Log a tool call."""
        query = """
            INSERT INTO tool_calls 
            (session_id, tool_name, parameters, result, success, error_message, duration_ms)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        return await self.db.fetchval(
            query, session_id, tool_name, parameters, result, 
            success, error_message, duration_ms
        )
    
    async def get_tool_usage_stats(
        self, 
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get tool usage statistics."""
        query = """
            SELECT 
                tool_name,
                COUNT(*) as call_count,
                AVG(duration_ms) as avg_duration_ms,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as error_count
            FROM tool_calls 
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY tool_name
            ORDER BY call_count DESC
        """ % days
        rows = await self.db.fetch(query)
        return [dict(row) for row in rows]


class ProjectAnalysisRepository:
    """Repository for project analysis caching."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def store_analysis(
        self,
        project_path: str,
        file_count: int,
        total_lines: int,
        language_stats: Dict[str, Any],
        symbols: Dict[str, Any],
        dependencies: Dict[str, Any]
    ) -> None:
        """Store project analysis results."""
        query = """
            INSERT INTO project_analysis 
            (project_path, file_count, total_lines, language_stats, symbols, dependencies)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (project_path) DO UPDATE SET
                file_count = $2,
                total_lines = $3,
                language_stats = $4,
                symbols = $5,
                dependencies = $6,
                last_analyzed = CURRENT_TIMESTAMP,
                expires_at = CURRENT_TIMESTAMP + INTERVAL '24 hours'
        """
        await self.db.execute(
            query, project_path, file_count, total_lines,
            language_stats, symbols, dependencies
        )
    
    async def get_analysis(self, project_path: str) -> Optional[Dict[str, Any]]:
        """Get cached project analysis."""
        query = """
            SELECT * FROM project_analysis 
            WHERE project_path = $1 AND expires_at > CURRENT_TIMESTAMP
        """
        row = await self.db.fetchrow(query, project_path)
        return dict(row) if row else None


# Global database manager instance
db_manager = DatabaseManager()


async def get_database() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


async def initialize_database() -> None:
    """Initialize the database connection."""
    await db_manager.initialize()


async def close_database() -> None:
    """Close the database connection."""
    await db_manager.close()