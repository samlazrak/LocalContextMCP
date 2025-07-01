"""
Database models and schema definitions for MCP Server.
Defines the structure for session management, tool calls, and caching.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import json


@dataclass
class MCPSession:
    """Represents an MCP session."""
    
    id: Optional[int] = None
    session_id: str = ""
    user_id: Optional[str] = None
    project_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "project_path": self.project_path,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None
        }


@dataclass
class ToolCall:
    """Represents a tool call record."""
    
    id: Optional[int] = None
    session_id: str = ""
    tool_name: str = ""
    server_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.result is None:
            self.result = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "server_name": self.server_name,
            "parameters": self.parameters,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class ProjectCache:
    """Represents cached project analysis data."""
    
    id: Optional[int] = None
    project_path: str = ""
    analysis_data: Optional[Dict[str, Any]] = None
    file_count: Optional[int] = None
    symbol_count: Optional[int] = None
    last_updated: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.analysis_data is None:
            self.analysis_data = {}
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()
        if self.expires_at is None:
            # Default 24 hour expiration
            from datetime import timedelta
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "project_path": self.project_path,
            "analysis_data": self.analysis_data,
            "file_count": self.file_count,
            "symbol_count": self.symbol_count,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class CompletionCache:
    """Represents cached code completion data."""
    
    id: Optional[int] = None
    file_path: str = ""
    context_hash: str = ""
    line_number: int = 0
    column_number: int = 0
    completions: Optional[List[Dict[str, Any]]] = None
    model_used: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.completions is None:
            self.completions = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.expires_at is None:
            # Default 1 hour expiration
            from datetime import timedelta
            self.expires_at = datetime.utcnow() + timedelta(hours=1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "context_hash": self.context_hash,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "completions": self.completions,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class ModelUsage:
    """Represents LLM model usage statistics."""
    
    id: Optional[int] = None
    model_name: str = ""
    endpoint: Optional[str] = None
    request_count: int = 0
    total_tokens: int = 0
    total_duration_ms: int = 0
    average_response_time: Optional[float] = None
    last_used: Optional[datetime] = None
    date_created: Optional[date] = None
    
    def __post_init__(self):
        if self.last_used is None:
            self.last_used = datetime.utcnow()
        if self.date_created is None:
            self.date_created = datetime.utcnow().date()
        if self.request_count > 0 and self.total_duration_ms > 0:
            self.average_response_time = self.total_duration_ms / self.request_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "model_name": self.model_name,
            "endpoint": self.endpoint,
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
            "average_response_time": self.average_response_time,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "date_created": self.date_created.isoformat() if self.date_created else None
        }


@dataclass
class ServerHealth:
    """Represents server health monitoring data."""
    
    id: Optional[int] = None
    server_name: str = ""
    status: str = ""  # running, stopped, error
    last_check: Optional[datetime] = None
    response_time_ms: Optional[int] = None
    error_count: int = 0
    uptime_seconds: int = 0
    memory_usage_mb: Optional[int] = None
    cpu_usage_percent: Optional[float] = None
    
    def __post_init__(self):
        if self.last_check is None:
            self.last_check = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "server_name": self.server_name,
            "status": self.status,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "response_time_ms": self.response_time_ms,
            "error_count": self.error_count,
            "uptime_seconds": self.uptime_seconds,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent
        }


@dataclass
class UserPreference:
    """Represents user preferences and settings."""
    
    id: Optional[int] = None
    user_id: str = ""
    preference_key: str = ""
    preference_value: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.preference_value is None:
            self.preference_value = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "preference_key": self.preference_key,
            "preference_value": self.preference_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class FileWatchEvent:
    """Represents file system watch events."""
    
    id: Optional[int] = None
    project_path: str = ""
    file_path: str = ""
    event_type: str = ""  # created, modified, deleted, moved
    old_path: Optional[str] = None  # for move events
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "project_path": self.project_path,
            "file_path": self.file_path,
            "event_type": self.event_type,
            "old_path": self.old_path,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# Database schema as SQL string for migration purposes
DATABASE_SCHEMA = """
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- MCP Sessions table
CREATE TABLE IF NOT EXISTS mcp_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    project_path TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tool calls logging table
CREATE TABLE IF NOT EXISTS mcp_tool_calls (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES mcp_sessions(session_id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    server_name VARCHAR(255),
    parameters JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    duration_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Project analysis cache
CREATE TABLE IF NOT EXISTS mcp_project_cache (
    id SERIAL PRIMARY KEY,
    project_path TEXT UNIQUE NOT NULL,
    analysis_data JSONB NOT NULL DEFAULT '{}',
    file_count INTEGER,
    symbol_count INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours')
);

-- Code completions cache
CREATE TABLE IF NOT EXISTS mcp_completion_cache (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    context_hash VARCHAR(64) NOT NULL,
    line_number INTEGER NOT NULL,
    column_number INTEGER NOT NULL,
    completions JSONB NOT NULL DEFAULT '[]',
    model_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    UNIQUE(file_path, context_hash, line_number, column_number)
);

-- AI model usage statistics
CREATE TABLE IF NOT EXISTS mcp_model_usage (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    endpoint VARCHAR(255),
    request_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_duration_ms BIGINT DEFAULT 0,
    average_response_time FLOAT,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_created DATE DEFAULT CURRENT_DATE,
    UNIQUE(model_name, date_created)
);

-- Server health monitoring
CREATE TABLE IF NOT EXISTS mcp_server_health (
    id SERIAL PRIMARY KEY,
    server_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    uptime_seconds BIGINT DEFAULT 0,
    memory_usage_mb INTEGER,
    cpu_usage_percent FLOAT
);

-- User preferences and settings
CREATE TABLE IF NOT EXISTS mcp_user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    preference_key VARCHAR(255) NOT NULL,
    preference_value JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, preference_key)
);

-- File watch history
CREATE TABLE IF NOT EXISTS mcp_file_watch_events (
    id SERIAL PRIMARY KEY,
    project_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    old_path TEXT,
    size_bytes BIGINT,
    checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_last_activity ON mcp_sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_user_id ON mcp_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_project_path ON mcp_sessions(project_path);

CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_session_id ON mcp_tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_tool_name ON mcp_tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_created_at ON mcp_tool_calls(created_at);

CREATE INDEX IF NOT EXISTS idx_mcp_project_cache_expires_at ON mcp_project_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_mcp_completion_cache_expires_at ON mcp_completion_cache(expires_at);

CREATE INDEX IF NOT EXISTS idx_mcp_model_usage_model_name ON mcp_model_usage(model_name);
CREATE INDEX IF NOT EXISTS idx_mcp_model_usage_date_created ON mcp_model_usage(date_created);

CREATE INDEX IF NOT EXISTS idx_mcp_server_health_server_name ON mcp_server_health(server_name);
CREATE INDEX IF NOT EXISTS idx_mcp_server_health_last_check ON mcp_server_health(last_check);

CREATE INDEX IF NOT EXISTS idx_mcp_user_preferences_user_id ON mcp_user_preferences(user_id);

CREATE INDEX IF NOT EXISTS idx_mcp_file_watch_project_path ON mcp_file_watch_events(project_path);
CREATE INDEX IF NOT EXISTS idx_mcp_file_watch_created_at ON mcp_file_watch_events(created_at);

-- JSONB GIN indexes for better JSON query performance
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_metadata_gin ON mcp_sessions USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_parameters_gin ON mcp_tool_calls USING GIN (parameters);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_result_gin ON mcp_tool_calls USING GIN (result);
CREATE INDEX IF NOT EXISTS idx_mcp_project_cache_analysis_gin ON mcp_project_cache USING GIN (analysis_data);
CREATE INDEX IF NOT EXISTS idx_mcp_completion_cache_completions_gin ON mcp_completion_cache USING GIN (completions);
CREATE INDEX IF NOT EXISTS idx_mcp_user_preferences_value_gin ON mcp_user_preferences USING GIN (preference_value);
"""