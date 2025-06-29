-- Table for schema versioning
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Table for storing chat messages
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    session_id TEXT,
    role TEXT, -- 'user' or 'assistant'
    content TEXT,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing context chunks (for retrieval)
CREATE TABLE IF NOT EXISTS context_chunks (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    chunk_index INTEGER,
    content TEXT,
    embedding BYTEA, -- store vector embedding for semantic search
    message_id INTEGER REFERENCES messages(id),
    start_offset INTEGER,
    end_offset INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Table for users
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_context_chunks_session_chunk ON context_chunks(session_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_context_chunks_message_id ON context_chunks(message_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id); 