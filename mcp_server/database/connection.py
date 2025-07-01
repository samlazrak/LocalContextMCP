"""
Database connection management for MCP Server.
Provides connection pooling, transaction management, and error handling.
"""

import asyncio
import asyncpg
import contextlib
from typing import Optional, AsyncGenerator, Any, Dict, List
from contextlib import asynccontextmanager

from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages PostgreSQL connections and provides database operations."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.config = get_config().database
        
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        try:
            logger.info("Initializing database connection pool")
            
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                command_timeout=60,
                server_settings={
                    'application_name': 'mcp_server',
                    'jit': 'off'  # Disable JIT for better predictability
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            logger.info(
                "Database connection pool initialized",
                host=self.config.host,
                database=self.config.database,
                min_connections=self.config.min_connections,
                max_connections=self.config.max_connections
            )
            
        except Exception as e:
            logger.error("Failed to initialize database connection pool", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            logger.info("Closing database connection pool")
            await self.pool.close()
            self.pool = None
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Get a database connection from the pool.
        
        Usage:
            async with db_manager.get_connection() as conn:
                result = await conn.fetch("SELECT * FROM table")
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        connection = None
        try:
            connection = await self.pool.acquire()
            yield connection
        except Exception as e:
            logger.error("Database connection error", error=str(e))
            raise
        finally:
            if connection:
                await self.pool.release(connection)
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Get a database connection with transaction management.
        
        Usage:
            async with db_manager.transaction() as conn:
                await conn.execute("INSERT INTO table VALUES ($1)", value)
                # Transaction auto-commits on success, rolls back on exception
        """
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def execute(self, query: str, *args, **kwargs) -> str:
        """
        Execute a SQL command that doesn't return rows.
        
        Args:
            query: SQL query string
            *args: Query parameters
            **kwargs: Additional parameters
            
        Returns:
            Command status string
        """
        async with self.get_connection() as conn:
            try:
                result = await conn.execute(query, *args, **kwargs)
                logger.debug("SQL command executed", query=query, args=args, result=result)
                return result
            except Exception as e:
                logger.error("SQL execution error", query=query, args=args, error=str(e))
                raise
    
    async def fetch(self, query: str, *args, **kwargs) -> List[asyncpg.Record]:
        """
        Execute a SQL query and return all rows.
        
        Args:
            query: SQL query string
            *args: Query parameters
            **kwargs: Additional parameters
            
        Returns:
            List of records
        """
        async with self.get_connection() as conn:
            try:
                result = await conn.fetch(query, *args, **kwargs)
                logger.debug("SQL query executed", query=query, args=args, rows=len(result))
                return result
            except Exception as e:
                logger.error("SQL query error", query=query, args=args, error=str(e))
                raise
    
    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[asyncpg.Record]:
        """
        Execute a SQL query and return the first row.
        
        Args:
            query: SQL query string
            *args: Query parameters
            **kwargs: Additional parameters
            
        Returns:
            First record or None
        """
        async with self.get_connection() as conn:
            try:
                result = await conn.fetchrow(query, *args, **kwargs)
                logger.debug("SQL query executed", query=query, args=args, found=result is not None)
                return result
            except Exception as e:
                logger.error("SQL query error", query=query, args=args, error=str(e))
                raise
    
    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        """
        Execute a SQL query and return a single value.
        
        Args:
            query: SQL query string
            *args: Query parameters
            **kwargs: Additional parameters
            
        Returns:
            Single value or None
        """
        async with self.get_connection() as conn:
            try:
                result = await conn.fetchval(query, *args, **kwargs)
                logger.debug("SQL query executed", query=query, args=args, value=result)
                return result
            except Exception as e:
                logger.error("SQL query error", query=query, args=args, error=str(e))
                raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check database health and return status information.
        
        Returns:
            Dictionary with health status
        """
        if not self.pool:
            return {
                "status": "error",
                "message": "Database pool not initialized"
            }
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with self.get_connection() as conn:
                # Test basic connectivity
                await conn.execute("SELECT 1")
                
                # Get database info
                db_version = await conn.fetchval("SELECT version()")
                db_size = await conn.fetchval(
                    "SELECT pg_size_pretty(pg_database_size($1))",
                    self.config.database
                )
                
                # Get connection pool stats
                pool_stats = {
                    "size": self.pool.get_size(),
                    "min_size": self.pool.get_min_size(),
                    "max_size": self.pool.get_max_size(),
                    "idle_connections": self.pool.get_idle_size()
                }
                
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "database_version": db_version,
                "database_size": db_size,
                "pool_stats": pool_stats
            }
            
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "error",
                "message": str(e)
            }


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


# Convenience functions for common operations
async def execute_query(query: str, *args, **kwargs) -> str:
    """Execute a SQL command."""
    return await db_manager.execute(query, *args, **kwargs)


async def fetch_all(query: str, *args, **kwargs) -> List[asyncpg.Record]:
    """Fetch all rows from a query."""
    return await db_manager.fetch(query, *args, **kwargs)


async def fetch_one(query: str, *args, **kwargs) -> Optional[asyncpg.Record]:
    """Fetch one row from a query."""
    return await db_manager.fetchrow(query, *args, **kwargs)


async def fetch_value(query: str, *args, **kwargs) -> Any:
    """Fetch a single value from a query."""
    return await db_manager.fetchval(query, *args, **kwargs)