# 🚀 Quick Start Guide - LocalContextMCP

## Overview
LocalContextMCP provides comprehensive IDE-like features for code completion, analysis, and AI assistance with **local LLM integration** (no API keys required for core functionality).

## Quick Setup (5 minutes)

### 1. Basic Installation
```bash
# Clone and enter directory
git clone <repository-url>
cd LocalContextMCP

# Install dependencies
pip install -r requirements.txt

# Run local DeepSeek setup (optional but recommended)
./scripts/setup_local_deepseek.sh

# Copy environment template
cp env.example .env
```

### 2. Environment Configuration
Edit your `.env` file:

```bash
# DeepSeek Configuration (Local)
DEEPSEEK_API_BASE=http://localhost:8000/v1
DEEPSEEK_MODEL=deepseek-coder

# Granite Configuration (Local via Ollama)
GRANITE_API_BASE=http://localhost:11434/v1

# Database Configuration
PGHOST=localhost
PGPORT=5432
PGDATABASE=mcp_memory
PGUSER=postgres
PGPASSWORD=postgres

# Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
```

### 3. Start Services

#### Option A: Local Development (Recommended)
```bash
# Start Ollama for Granite (in terminal 1)
ollama serve

# Start DeepSeek locally (in terminal 2)
# Choose your preferred method from setup script:
# - Ollama: ./start_deepseek_ollama.sh
# - vLLM: ./start_deepseek_vllm.sh  
# - WebUI: ./start_deepseek_webui.sh

# Start MCP server (in terminal 3)
python mcp_server.py
```

#### Option B: Docker
```bash
# Build and start all services
docker-compose up --build

# Check status
docker-compose ps
```

### 4. Verify Installation
```bash
# Health check
curl http://localhost:8080/health

# List available tools
curl -X POST http://localhost:8080/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools_list","id":1}'
```

## Local LLM Models

### DeepSeek-Coder (Port 8000)
- **Purpose**: Complex analysis, debugging, generation
- **Setup**: Run `./scripts/setup_local_deepseek.sh`
- **Models**: deepseek-coder-6.7b-instruct (recommended)
- **Alternatives**: vLLM, Ollama, Text Generation WebUI

### Granite 3.1 8B (Port 11434)  
- **Purpose**: Fast completions, basic analysis
- **Setup**: `ollama pull granite3.1:8b`
- **Server**: `ollama serve`

## Available Features

### Core Tools
- **Git Operations**: `git_status`, `git_commit`, `git_diff`
- **File System**: `read_file`, `write_file`, `list_directory`
- **Database**: SQLite and PostgreSQL operations
- **Web Search**: DuckDuckGo integration
- **Memory**: Persistent context storage

### AI-Enhanced Features
- **Code Completion**: Context-aware completions
- **Project Analysis**: Comprehensive project insights
- **AI Debugging**: Error analysis and solutions
- **Code Generation**: AI-powered code creation
- **Intelligent Search**: Semantic code search

## Testing the Setup

### Basic functionality
```bash
# Get current time
curl -X POST http://localhost:8080/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools_call","params":{"tool":"time"},"id":1}'

# Git status
curl -X POST http://localhost:8080/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools_call","params":{"tool":"git","params":{"command":"status"}},"id":2}'
```

### AI features (requires local LLMs)
```bash
# Test DeepSeek connection
curl -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-coder","messages":[{"role":"user","content":"Hello"}]}'

# Test comprehensive code completion
curl -X POST http://localhost:8080/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"comprehensive_code_completion","params":{"file_path":"test.py","line":1,"column":1,"context":"def hello","project_path":"."},"id":3}'
```

## IDE Integration

### Cursor Integration
1. Copy `.cursor/mcp.json` to your project
2. Configure the MCP server endpoint: `http://localhost:8080`
3. Restart Cursor

### VSCode Integration
1. Install MCP extension
2. Add server configuration:
```json
{
  "mcp.servers": {
    "localcontext": {
      "endpoint": "http://localhost:8080",
      "name": "LocalContextMCP"
    }
  }
}
```

## Troubleshooting

### Common Issues

#### "DeepSeek connection failed"
- Ensure DeepSeek is running: `curl http://localhost:8000/v1/models`
- Check port conflicts: `lsof -i :8000`
- Verify model is loaded correctly

#### "Ollama/Granite not responding"
- Start Ollama: `ollama serve`
- Pull model: `ollama pull granite3.1:8b`
- Test connection: `curl http://localhost:11434/api/tags`

#### "Database connection failed"
- Install PostgreSQL: `brew install postgresql` (macOS) or `apt install postgresql` (Ubuntu)
- Create database: `createdb mcp_memory`
- Update `.env` with correct credentials

### Performance Tips
- Use SSD storage for better model loading
- Allocate sufficient RAM (8GB+ recommended)
- Consider GPU acceleration for larger models
- Use cached models to reduce startup time

## Next Steps
1. **Explore Advanced Features**: Try `comprehensive_mcp_server.py` for enhanced AI capabilities
2. **Customize Tools**: Add your own MCP tools and integrations
3. **Scale Setup**: Use Docker Compose for production deployment
4. **Monitor Performance**: Set up Prometheus/Grafana monitoring

## Getting Help
- Check `SETUP_COMPLETE.md` for detailed setup status
- Review logs: `tail -f logs/mcp_server.log`
- Run diagnostic: `python test_server.py`
- GitHub Issues: Report bugs and request features

---

**🎯 Goal**: Provide Cursor-like IDE features with fully local LLM processing - no API keys required!