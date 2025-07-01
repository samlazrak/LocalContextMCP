-- LocalContextMCP Database Schema
-- Creates tables for MCP sessions, memories, code analysis, and monitoring

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector" IF EXISTS;

-- Sessions table for tracking MCP connections
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    project_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true
);

-- Memory storage for conversation context
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text',
    embedding VECTOR(384), -- For sentence-transformers embeddings
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tool call logging and analytics
CREATE TABLE IF NOT EXISTS tool_calls (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    parameters JSONB,
    result JSONB,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Project analysis cache
CREATE TABLE IF NOT EXISTS project_analysis (
    id SERIAL PRIMARY KEY,
    project_path TEXT UNIQUE NOT NULL,
    file_count INTEGER,
    total_lines INTEGER,
    language_stats JSONB DEFAULT '{}',
    symbols JSONB DEFAULT '{}',
    dependencies JSONB DEFAULT '{}',
    last_analyzed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours')
);

-- Code completion cache
CREATE TABLE IF NOT EXISTS completions_cache (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    column_number INTEGER NOT NULL,
    context_hash VARCHAR(64) NOT NULL,
    completions JSONB NOT NULL,
    model_used VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    UNIQUE(file_path, line_number, column_number, context_hash)
);

-- File watch events for project monitoring
CREATE TABLE IF NOT EXISTS file_events (
    id SERIAL PRIMARY KEY,
    project_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    event_type VARCHAR(20) NOT NULL, -- created, modified, deleted, moved
    old_path TEXT, -- for move events
    file_size BIGINT,
    checksum VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Server health and performance metrics
CREATE TABLE IF NOT EXISTS server_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active, last_activity);
CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_content_search ON memories USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_tool_calls_session_time ON tool_calls(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name ON tool_calls(tool_name, created_at);
CREATE INDEX IF NOT EXISTS idx_project_analysis_path ON project_analysis(project_path);
CREATE INDEX IF NOT EXISTS idx_project_analysis_expires ON project_analysis(expires_at);
CREATE INDEX IF NOT EXISTS idx_completions_cache_expires ON completions_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_file_events_project_time ON file_events(project_path, created_at);
CREATE INDEX IF NOT EXISTS idx_server_metrics_time ON server_metrics(metric_name, timestamp);

-- Vector similarity search index (if vector extension is available)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    END IF;
END
$$;

-- Functions for automatic cleanup and maintenance
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS void AS $$
BEGIN
    -- Clean up expired project analysis
    DELETE FROM project_analysis WHERE expires_at < CURRENT_TIMESTAMP;
    
    -- Clean up expired completion cache
    DELETE FROM completions_cache WHERE expires_at < CURRENT_TIMESTAMP;
    
    -- Clean up old file events (keep last 7 days)
    DELETE FROM file_events WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
    
    -- Clean up old tool calls (keep last 30 days)
    DELETE FROM tool_calls WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Clean up old server metrics (keep last 30 days)
    DELETE FROM server_metrics WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Update sessions last_activity on new tool calls
    UPDATE sessions SET last_activity = CURRENT_TIMESTAMP 
    WHERE session_id IN (
        SELECT DISTINCT session_id FROM tool_calls 
        WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 minute'
    );
END;
$$ LANGUAGE plpgsql;

-- Function to update memory embeddings (placeholder for when vector extension is available)
CREATE OR REPLACE FUNCTION update_memory_embedding()
RETURNS TRIGGER AS $$
BEGIN
    -- This would be called by the application layer to update embeddings
    -- when new memories are added or updated
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic timestamp updates
CREATE TRIGGER update_memory_timestamp
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_memory_embedding();

-- Create a sample session for testing
INSERT INTO sessions (session_id, user_id, project_path, metadata)
VALUES (
    'test_session_001',
    'test_user',
    '/workspace',
    '{"environment": "development", "client": "test"}'
) ON CONFLICT (session_id) DO NOTHING;

COMMIT;