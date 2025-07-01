-- MCP Server Database Schema
-- Clean implementation for essential MCP functionality

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

-- Model usage statistics
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_last_activity ON mcp_sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_user_id ON mcp_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_project_path ON mcp_sessions(project_path);

CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_session_id ON mcp_tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_tool_name ON mcp_tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_created_at ON mcp_tool_calls(created_at);

CREATE INDEX IF NOT EXISTS idx_mcp_model_usage_model_name ON mcp_model_usage(model_name);
CREATE INDEX IF NOT EXISTS idx_mcp_model_usage_date_created ON mcp_model_usage(date_created);

CREATE INDEX IF NOT EXISTS idx_mcp_server_health_server_name ON mcp_server_health(server_name);
CREATE INDEX IF NOT EXISTS idx_mcp_server_health_last_check ON mcp_server_health(last_check);

CREATE INDEX IF NOT EXISTS idx_mcp_user_preferences_user_id ON mcp_user_preferences(user_id);

-- JSONB GIN indexes for better JSON query performance
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_metadata_gin ON mcp_sessions USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_parameters_gin ON mcp_tool_calls USING GIN (parameters);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_result_gin ON mcp_tool_calls USING GIN (result);
CREATE INDEX IF NOT EXISTS idx_mcp_user_preferences_value_gin ON mcp_user_preferences USING GIN (preference_value);

-- Create functions for automatic cleanup
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS void AS $$
BEGIN
    -- Clean up old tool calls (keep last 30 days)
    DELETE FROM mcp_tool_calls WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Clean up inactive sessions (keep last 7 days)
    DELETE FROM mcp_sessions WHERE last_activity < CURRENT_TIMESTAMP - INTERVAL '7 days';
    
    -- Clean up old model usage stats (keep last 90 days)
    DELETE FROM mcp_model_usage WHERE date_created < CURRENT_DATE - INTERVAL '90 days';
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
        COALESCE(NEW.duration_ms, 0),
        NEW.created_at
    )
    ON CONFLICT (model_name, date_created) DO UPDATE SET
        request_count = mcp_model_usage.request_count + 1,
        total_duration_ms = mcp_model_usage.total_duration_ms + COALESCE(NEW.duration_ms, 0),
        average_response_time = (mcp_model_usage.total_duration_ms + COALESCE(NEW.duration_ms, 0)) / (mcp_model_usage.request_count + 1),
        last_used = NEW.created_at;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for model usage statistics (only for LLM-related tool calls)
DROP TRIGGER IF EXISTS trigger_update_model_usage ON mcp_tool_calls;
CREATE TRIGGER trigger_update_model_usage
    AFTER INSERT ON mcp_tool_calls
    FOR EACH ROW
    WHEN (NEW.result ? 'model_used')
    EXECUTE FUNCTION update_model_usage_stats();

-- Initial health data
INSERT INTO mcp_server_health (server_name, status, response_time_ms, error_count)
VALUES 
    ('mcp_server', 'running', 0, 0),
    ('database', 'running', 0, 0)
ON CONFLICT DO NOTHING;

-- Sample data for development (only in development environment)
-- This will be ignored in production due to the conditional check
DO $$
BEGIN
    -- Only insert sample data if we're in a development environment
    IF current_setting('application_name', true) = 'mcp_server_dev' THEN
        -- Sample session
        INSERT INTO mcp_sessions (session_id, user_id, project_path, metadata)
        VALUES (
            'sample-session-001',
            'dev-user',
            '/workspace',
            '{"environment": "development", "created_by": "init_script"}'
        ) ON CONFLICT DO NOTHING;
        
        -- Sample tool call
        INSERT INTO mcp_tool_calls (
            session_id, tool_name, server_name, parameters, result, duration_ms, success
        ) VALUES (
            'sample-session-001',
            'readfile',
            'mcp_server',
            '{"file_path": "/workspace/README.md"}',
            '{"success": true, "data": {"content": "Sample content"}}',
            150,
            true
        ) ON CONFLICT DO NOTHING;
    END IF;
END $$;

COMMIT;