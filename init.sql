-- Comprehensive MCP Server Database Schema
-- Initialize database tables and indexes

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- MCP Sessions table
CREATE TABLE IF NOT EXISTS mcp_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    project_path TEXT,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    INDEX USING GIN (metadata)
);

-- Tool calls logging table
CREATE TABLE IF NOT EXISTS mcp_tool_calls (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES mcp_sessions(session_id),
    tool_name VARCHAR(255) NOT NULL,
    server_name VARCHAR(255),
    parameters JSONB,
    result JSONB,
    duration_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX USING GIN (parameters),
    INDEX USING GIN (result)
);

-- Project analysis cache
CREATE TABLE IF NOT EXISTS mcp_project_cache (
    id SERIAL PRIMARY KEY,
    project_path TEXT UNIQUE NOT NULL,
    analysis_data JSONB NOT NULL,
    file_count INTEGER,
    symbol_count INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
    INDEX USING GIN (analysis_data)
);

-- Code completions cache
CREATE TABLE IF NOT EXISTS mcp_completion_cache (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    context_hash VARCHAR(64) NOT NULL,
    line_number INTEGER,
    column_number INTEGER,
    completions JSONB NOT NULL,
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
    status VARCHAR(50) NOT NULL, -- running, stopped, error
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
    preference_value JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, preference_key)
);

-- File watch history
CREATE TABLE IF NOT EXISTS mcp_file_watch_events (
    id SERIAL PRIMARY KEY,
    project_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- created, modified, deleted, moved
    old_path TEXT, -- for move events
    size_bytes BIGINT,
    checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX USING HASH (project_path),
    INDEX USING HASH (file_path)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_last_activity ON mcp_sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_session_created ON mcp_tool_calls(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_tool_name ON mcp_tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_mcp_project_cache_expires ON mcp_project_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_mcp_completion_cache_expires ON mcp_completion_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_mcp_model_usage_date ON mcp_model_usage(date_created);
CREATE INDEX IF NOT EXISTS idx_mcp_server_health_name_check ON mcp_server_health(server_name, last_check);
CREATE INDEX IF NOT EXISTS idx_mcp_file_watch_project_created ON mcp_file_watch_events(project_path, created_at);

-- Create functions for automatic cleanup
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    -- Clean up expired project cache
    DELETE FROM mcp_project_cache WHERE expires_at < CURRENT_TIMESTAMP;
    
    -- Clean up expired completion cache
    DELETE FROM mcp_completion_cache WHERE expires_at < CURRENT_TIMESTAMP;
    
    -- Clean up old tool calls (keep last 30 days)
    DELETE FROM mcp_tool_calls WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Clean up old file watch events (keep last 7 days)
    DELETE FROM mcp_file_watch_events WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Create function to update session activity
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE mcp_sessions 
    SET last_activity = CURRENT_TIMESTAMP 
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic session activity update
DROP TRIGGER IF EXISTS trigger_update_session_activity ON mcp_tool_calls;
CREATE TRIGGER trigger_update_session_activity
    AFTER INSERT ON mcp_tool_calls
    FOR EACH ROW
    EXECUTE FUNCTION update_session_activity();

-- Create function to update model usage statistics
CREATE OR REPLACE FUNCTION update_model_usage_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO mcp_model_usage (model_name, request_count, total_duration_ms, last_used)
    VALUES (
        COALESCE(NEW.result->>'model_used', 'unknown'),
        1,
        NEW.duration_ms,
        NEW.created_at
    )
    ON CONFLICT (model_name, date_created) DO UPDATE SET
        request_count = mcp_model_usage.request_count + 1,
        total_duration_ms = mcp_model_usage.total_duration_ms + NEW.duration_ms,
        average_response_time = (mcp_model_usage.total_duration_ms + NEW.duration_ms) / (mcp_model_usage.request_count + 1),
        last_used = NEW.created_at;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for model usage statistics
DROP TRIGGER IF EXISTS trigger_update_model_usage ON mcp_tool_calls;
CREATE TRIGGER trigger_update_model_usage
    AFTER INSERT ON mcp_tool_calls
    FOR EACH ROW
    WHEN (NEW.tool_name IN ('comprehensive_code_completion', 'ai_assisted_debugging', 'code_generation', 'project_analysis'))
    EXECUTE FUNCTION update_model_usage_stats();

-- Initial data
INSERT INTO mcp_server_health (server_name, status, response_time_ms, error_count)
VALUES 
    ('comprehensive-mcp', 'running', 0, 0),
    ('filesystem', 'running', 0, 0),
    ('git', 'running', 0, 0),
    ('postgres', 'running', 0, 0)
ON CONFLICT DO NOTHING;

-- Set up cleanup job (requires pg_cron extension in production)
-- SELECT cron.schedule('cleanup-expired-cache', '0 2 * * *', 'SELECT cleanup_expired_cache();');

COMMIT;