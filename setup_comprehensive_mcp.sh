#!/bin/bash

# Comprehensive MCP Server Setup Script
# Sets up the complete environment for Void IDE integration

set -e

echo "🚀 Setting up Comprehensive MCP Server for Void IDE..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

# Check system requirements
print_header "Checking system requirements..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ $(echo "$PYTHON_VERSION < 3.8" | bc -l) ]]; then
    print_error "Python 3.8+ is required, found $PYTHON_VERSION"
    exit 1
fi
print_status "Python $PYTHON_VERSION found ✓"

# Check Node.js for MCP servers
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    print_status "Node.js $NODE_VERSION found ✓"
else
    print_warning "Node.js not found - some MCP servers will not be available"
fi

# Check Docker
if command -v docker &> /dev/null; then
    print_status "Docker found ✓"
else
    print_warning "Docker not found - container-based MCP servers will not be available"
fi

# Install Python dependencies
print_header "Installing Python dependencies..."
pip3 install -r requirements.txt
print_status "Python dependencies installed ✓"

# Setup PostgreSQL database
print_header "Setting up PostgreSQL database..."
if command -v psql &> /dev/null; then
    # Check if database exists
    DB_NAME="comprehensive_mcp"
    if psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
        print_status "Database '$DB_NAME' already exists ✓"
    else
        print_status "Creating database '$DB_NAME'..."
        createdb $DB_NAME
        print_status "Database created ✓"
    fi
    
    # Initialize schema
    print_status "Initializing database schema..."
    python3 -c "
import asyncio
import asyncpg
import os

async def init_db():
    conn = await asyncpg.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', '5432')),
        database='comprehensive_mcp',
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', 'postgres')
    )
    
    # Create tables for MCP server state and logs
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS mcp_sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) UNIQUE,
            project_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS mcp_tool_calls (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255),
            tool_name VARCHAR(255),
            parameters JSONB,
            result JSONB,
            duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS mcp_project_cache (
            id SERIAL PRIMARY KEY,
            project_path TEXT UNIQUE,
            analysis_data JSONB,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    await conn.close()
    print('Database schema initialized ✓')

asyncio.run(init_db())
"
else
    print_warning "PostgreSQL not found - database features will be limited"
fi

# Setup Local LLMs
print_header "Setting up local LLMs..."

# Setup Ollama for Granite 3.1 8B
if command -v ollama &> /dev/null; then
    print_status "Ollama found, installing Granite 3.1 8B..."
    ollama pull granite3.1:8b
    print_status "Granite 3.1 8B installed ✓"
else
    print_warning "Ollama not found. Installing..."
    curl -fsSL https://ollama.ai/install.sh | sh
    print_status "Ollama installed ✓"
    print_status "Pulling Granite 3.1 8B model..."
    ollama pull granite3.1:8b
    print_status "Granite 3.1 8B installed ✓"
fi

# Instructions for DeepSeek local setup
print_header "DeepSeek Local Setup Instructions"
print_status "To run DeepSeek locally, you need to:"
echo "  1. Download a local DeepSeek model (e.g., via Ollama, vLLM, or similar)"
echo "  2. Start the model server on port 8000 with OpenAI-compatible API"
echo "  3. Example with Ollama:"
echo "     ollama pull deepseek-coder"
echo "     ollama serve --port 8000"
echo "  4. Or use vLLM, Text Generation WebUI, or other OpenAI-compatible servers"
echo ""
print_warning "The server will work without DeepSeek but complex tasks will be limited"
print_warning "Update DEEPSEEK_API_BASE in .env to point to your local server"

# Install essential MCP servers
print_header "Installing essential MCP servers..."

# Official MCP servers
NPX_SERVERS=(
    "@modelcontextprotocol/server-github"
    "@modelcontextprotocol/server-sqlite"
    "@modelcontextprotocol/server-brave-search"
    "@modelcontextprotocol/server-fetch"
    "@modelcontextprotocol/server-puppeteer"
    "@modelcontextprotocol/server-memory"
    "@modelcontextprotocol/server-sequential-thinking"
    "@modelcontextprotocol/server-time"
    "@modelcontextprotocol/server-slack"
    "@modelcontextprotocol/server-notion"
    "@modelcontextprotocol/server-sentry"
)

for server in "${NPX_SERVERS[@]}"; do
    print_status "Installing $server..."
    npm install -g $server
done

print_status "MCP servers installed ✓"

# Create environment configuration
print_header "Creating environment configuration..."

cat > .env << 'EOF'
# Comprehensive MCP Server Configuration

# Database Configuration
PGHOST=localhost
PGPORT=5432
PGDATABASE=comprehensive_mcp
PGUSER=postgres
PGPASSWORD=your_postgres_password

# LLM Configuration (Local)
DEEPSEEK_API_BASE=http://localhost:8000/v1
DEEPSEEK_MODEL=deepseek-coder
GRANITE_API_BASE=http://localhost:11434/v1

# Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=8080
DEBUG=false

# Optional API Keys
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key
HUGGINGFACE_TOKEN=your_huggingface_token
SLACK_BOT_TOKEN=your_slack_bot_token
NOTION_TOKEN=your_notion_token
EOF

print_status "Environment configuration created ✓"
print_warning "Please edit .env file with your actual API keys and credentials"

# Create start script
print_header "Creating start script..."

cat > start_comprehensive_mcp.sh << 'EOF'
#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start Ollama in background if not running
if ! pgrep -f ollama >/dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 5
fi

# Start the comprehensive MCP server
echo "Starting Comprehensive MCP Server..."
python3 comprehensive_mcp_server.py
EOF

chmod +x start_comprehensive_mcp.sh
print_status "Start script created ✓"

# Create Void IDE configuration
print_header "Creating Void IDE configuration..."

cat > void_mcp_config.json << 'EOF'
{
  "mcp": {
    "servers": {
      "comprehensive": {
        "name": "Comprehensive MCP Server",
        "endpoint": "http://localhost:8080",
        "protocol": "http",
        "capabilities": [
          "code_completion",
          "project_analysis", 
          "debugging",
          "code_generation",
          "file_operations",
          "git_operations",
          "database_operations",
          "web_search",
          "ai_assistance"
        ],
        "models": {
          "local": "granite3.1:8b",
          "remote": "deepseek-coder"
        }
      }
    },
    "routing": {
      "code_completion": "comprehensive",
      "project_analysis": "comprehensive",
      "debugging": "comprehensive",
      "code_generation": "comprehensive"
    }
  }
}
EOF

print_status "Void IDE configuration created ✓"

# Create test script
print_header "Creating test script..."

cat > test_comprehensive_mcp.py << 'EOF'
#!/usr/bin/env python3
"""
Test script for Comprehensive MCP Server
"""

import asyncio
import aiohttp
import json

async def test_server():
    """Test the comprehensive MCP server"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing Comprehensive MCP Server...")
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print("✅ Health check passed")
                    print(f"   - Status: {health_data['status']}")
                    print(f"   - Components: {health_data['components']}")
                    print(f"   - Total tools: {health_data['total_tools']}")
                else:
                    print("❌ Health check failed")
                    return
        except Exception as e:
            print(f"❌ Could not connect to server: {e}")
            return
        
        # Test servers list
        try:
            async with session.get(f"{base_url}/api/servers") as response:
                if response.status == 200:
                    servers_data = await response.json()
                    print(f"✅ Found {len(servers_data['servers'])} MCP servers")
                    for server in servers_data['servers'][:5]:
                        status = server['status']
                        emoji = "🟢" if status == "running" else "🔴"
                        print(f"   {emoji} {server['name']}: {status}")
        except Exception as e:
            print(f"❌ Could not get servers list: {e}")
        
        # Test tools list
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools_list",
                "id": 1
            }
            async with session.post(base_url, json=payload) as response:
                if response.status == 200:
                    tools_data = await response.json()
                    if "result" in tools_data:
                        print(f"✅ Found {len(tools_data['result'])} total tools")
                        print("   Sample tools:")
                        for tool in tools_data['result'][:5]:
                            print(f"   - {tool}")
        except Exception as e:
            print(f"❌ Could not get tools list: {e}")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_server())
EOF

chmod +x test_comprehensive_mcp.py
print_status "Test script created ✓"

# Final instructions
print_header "Setup completed! 🎉"
echo ""
print_status "Next steps:"
echo "1. Edit .env file with your API keys and credentials"
echo "2. Start the server: ./start_comprehensive_mcp.sh"
echo "3. Test the server: python3 test_comprehensive_mcp.py"
echo "4. Configure Void IDE with void_mcp_config.json"
echo ""
print_status "The comprehensive MCP server provides:"
echo "   - 30+ integrated MCP servers"
echo "   - DeepSeek-Coder (local on port 8000)"
echo "   - Granite 3.1 8B (local via Ollama)"
echo "   - Advanced code completion and analysis"
echo "   - AI-powered debugging and generation"
echo "   - Full project context awareness"
echo ""
print_status "Documentation: README.md"
print_status "Health check: http://localhost:8080/health"
print_status "API docs: http://localhost:8080/api/servers"