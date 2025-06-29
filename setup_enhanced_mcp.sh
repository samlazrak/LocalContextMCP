#!/bin/bash

echo "🚀 Setting up Enhanced MCP Server for Cursor-like IDE Experience"
echo "================================================================"

# Check Python version
python_version=$(python3 --version 2>/dev/null || echo "Python not found")
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Install tree-sitter languages (requires compilation)
echo "🌳 Setting up tree-sitter parsers..."
python3 -c "
import tree_sitter
from tree_sitter import Language

# Create build directory
import os
os.makedirs('build', exist_ok=True)

try:
    # Build language parsers
    Language.build_library(
        'build/languages.so',
        [
            'tree-sitter-python',
            'tree-sitter-javascript', 
            'tree-sitter-typescript'
        ]
    )
    print('✅ Tree-sitter parsers built successfully')
except Exception as e:
    print(f'⚠️ Tree-sitter build failed: {e}')
    print('You may need to install git and a C compiler')
"

# Set up PostgreSQL extensions if needed
echo "🗄️ Setting up PostgreSQL extensions..."
export PGPASSWORD=${PGPASSWORD:-postgres}
psql -h ${PGHOST:-localhost} -p ${PGPORT:-5432} -U ${PGUSER:-postgres} -d ${PGDATABASE:-mcp_memory} -c "
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
" 2>/dev/null || echo "⚠️ Could not set up PostgreSQL extensions (database may not be running)"

# Create enhanced database schema
echo "📋 Creating enhanced database schema..."
psql -h ${PGHOST:-localhost} -p ${PGPORT:-5432} -U ${PGUSER:-postgres} -d ${PGDATABASE:-mcp_memory} -f - << 'EOF'
-- Enhanced schema for Cursor-like features
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL UNIQUE,
    language TEXT,
    framework TEXT,
    last_indexed TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS code_symbols (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    symbol_name TEXT NOT NULL,
    symbol_type TEXT NOT NULL, -- function, class, variable, etc.
    line_start INTEGER,
    line_end INTEGER,
    column_start INTEGER,
    column_end INTEGER,
    signature TEXT,
    docstring TEXT,
    embedding VECTOR(384),
    parent_symbol_id INTEGER REFERENCES code_symbols(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS file_dependencies (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    source_file TEXT NOT NULL,
    target_file TEXT NOT NULL,
    import_type TEXT, -- import, require, include
    import_name TEXT,
    line_number INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS code_completions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    context_hash TEXT NOT NULL,
    completion TEXT NOT NULL,
    score FLOAT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS diagnostics (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    column_number INTEGER,
    severity TEXT, -- error, warning, info
    message TEXT,
    source TEXT, -- linter, compiler, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_code_symbols_project_file ON code_symbols(project_id, file_path);
CREATE INDEX IF NOT EXISTS idx_code_symbols_name ON code_symbols(symbol_name);
CREATE INDEX IF NOT EXISTS idx_code_symbols_type ON code_symbols(symbol_type);
CREATE INDEX IF NOT EXISTS idx_file_dependencies_source ON file_dependencies(source_file);
CREATE INDEX IF NOT EXISTS idx_file_dependencies_target ON file_dependencies(target_file);
CREATE INDEX IF NOT EXISTS idx_diagnostics_file ON diagnostics(project_id, file_path);
CREATE INDEX IF NOT EXISTS idx_code_completions_hash ON code_completions(context_hash);
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(root_path);

-- Update existing tables if needed
DO $$ 
BEGIN
    -- Add any missing columns to existing tables
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='context_chunks' AND column_name='project_id') THEN
        ALTER TABLE context_chunks ADD COLUMN project_id INTEGER REFERENCES projects(id);
    END IF;
EXCEPTION WHEN others THEN
    -- Table doesn't exist, ignore
    NULL;
END $$;

EOF

echo "✅ Enhanced database schema created"

# Create sample environment file
if [ ! -f ".env" ]; then
    echo "📝 Creating sample .env file..."
    cp env.example .env
    echo "⚠️ Please edit .env with your actual configuration"
fi

# Create systemd service file (optional)
echo "🔧 Creating systemd service file..."
cat > enhanced-mcp-server.service << 'EOF'
[Unit]
Description=Enhanced MCP Server
After=network.target postgresql.service

[Service]
Type=simple
User=mcp
WorkingDirectory=/path/to/LocalContextMCP
Environment=PATH=/path/to/LocalContextMCP/venv/bin
ExecStart=/path/to/LocalContextMCP/venv/bin/python enhanced_mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "📋 Systemd service file created (enhanced-mcp-server.service)"
echo "   Edit paths and install with: sudo cp enhanced-mcp-server.service /etc/systemd/system/"

# Test the setup
echo "🧪 Testing enhanced MCP server..."
python3 -c "
try:
    import flask, jsonrpcserver, aiohttp, asyncpg
    import tree_sitter
    print('✅ All core dependencies imported successfully')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    print('Please run: pip install -r requirements.txt')
"

echo ""
echo "🎉 Enhanced MCP Server setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Ensure PostgreSQL is running with the pgvector extension"
echo "3. Ensure your desktop LLM is running and accessible"
echo "4. Start the enhanced server: python3 enhanced_mcp_server.py"
echo "5. Test with: curl -X GET http://localhost:8080/health"
echo ""
echo "Key improvements now available:"
echo "• Enhanced code completion with project context"
echo "• Semantic search across your codebase"
echo "• Project analysis and insights"
echo "• Async communication with desktop LLM"
echo "• Improved database schema for code intelligence"
echo ""
echo "See CURSOR_IMPROVEMENTS.md for detailed features and implementation guide" 