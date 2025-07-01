# Getting Started with LocalContextMCP

Welcome to LocalContextMCP! This guide will help you get up and running quickly.

## Prerequisites

- **Python 3.11+** 
- **PostgreSQL 15+** (or Docker)
- **LM Studio** (for local LLM inference)
- **Git** (for version control features)

## Quick Start Options

### Option 1: Automated Setup (Recommended)

```bash
# Make setup script executable and run it
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will guide you through:
- Creating a virtual environment
- Installing dependencies  
- Setting up the database
- Configuring environment variables
- Starting the development server

### Option 2: Docker (Easiest)

```bash
# Start with Docker Compose
docker-compose -f docker/docker-compose.yml up -d

# Check health
curl http://localhost:8080/health
```

### Option 3: Manual Setup

```bash
# 1. Clone and setup Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Setup environment variables
cp .env.example .env
# Edit .env with your settings

# 3. Setup database
createdb localcontextmcp
psql localcontextmcp < database/schema.sql

# 4. Start the server
python -m src
```

## Verify Installation

Once running, test these endpoints:

```bash
# Health check
curl http://localhost:8080/health

# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test file reading
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "tools/call",
    "params": {
      "name": "read_file",
      "arguments": {"file_path": "README.md"}
    },
    "id": 2
  }'
```

## LM Studio Setup

1. **Download LM Studio**: [lmstudio.ai](https://lmstudio.ai/)

2. **Load Models**:
   - For embeddings: `qwen2.5-coder-0.5B-instruct`
   - For completions: `qwen2.5-coder-14B-instruct` (or any preferred model)

3. **Start Local Server**: In LM Studio, go to "Local Server" and start it (usually port 1234)

4. **Test Connection**:
   ```bash
   curl http://localhost:1234/v1/models
   ```

## Available Tools

The server provides these MCP tools out of the box:

### File Operations
- `read_file` - Read file contents
- `write_file` - Write content to files  
- `list_files` - List directory contents

### Memory & Context
- `store_memory` - Store conversation context
- `search_memory` - Search stored memories

### Code Intelligence  
- `code_completion` - Get code completions
- `project_analysis` - Analyze project structure

### Git Operations
- `git_status` - Get repository status
- `git_commit` - Create commits

## Configuration

Key settings in your `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/localcontextmcp

# LM Studio  
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=qwen2.5-coder-0.5B-instruct

# Server
HOST=0.0.0.0
PORT=8080
LOG_LEVEL=INFO
```

## Development

```bash
# Run tests
pytest

# Development server with auto-reload
./scripts/setup.sh dev

# Format code
black src tests
flake8 src tests

# Type checking (if mypy is installed)
mypy src
```

## Troubleshooting

### Common Issues

**"Connection refused" to database**
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env
- For Docker: `docker-compose logs postgres`

**LM Studio not responding**  
- Verify LM Studio server is running on port 1234
- Check model is loaded in LM Studio
- Test: `curl http://localhost:1234/v1/models`

**Import errors**
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

**Port already in use**
- Change PORT in .env file
- Or stop conflicting service: `lsof -i :8080`

### Logs

- Development: Logs print to console
- Docker: `docker-compose logs mcp-server`
- File logs: `logs/` directory (if configured)

## Next Steps

1. **Explore the API**: Check `/api/tools` and `/health` endpoints
2. **Add Custom Tools**: Extend `src/mcp/tools/` 
3. **Configure LLM**: Set up DeepSeek or other providers
4. **Integrate**: Use with Claude Desktop or other MCP clients

## Architecture Overview

```
LocalContextMCP/
├── src/
│   ├── core/           # Configuration, database, LLM clients
│   ├── mcp/            # MCP server and protocol handlers  
│   │   ├── tools/      # Tool implementations
│   │   └── handlers/   # MCP request handlers
│   └── api/            # REST API endpoints
├── database/           # Database schema and migrations
├── docker/             # Docker configuration
├── tests/              # Test suite
└── scripts/            # Utility scripts
```

For detailed information, see the main [README.md](README.md).

## Support

- **Documentation**: README.md and code docstrings
- **Issues**: Use GitHub issues for bugs and feature requests
- **Development**: See CONTRIBUTING.md (if available)

Happy coding! 🚀