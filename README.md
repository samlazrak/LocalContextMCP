# MCP Server

A comprehensive Model Context Protocol (MCP) server built with modern Python practices. This server provides LLM integration, tool execution, and persistent session management with a clean, modular architecture.

## Features

- **🔌 Multi-LLM Support**: Compatible with LM Studio, Ollama, and OpenAI
- **🛠️ Tool System**: Extensible tool architecture with built-in filesystem operations
- **💾 Persistent Storage**: PostgreSQL-based session and execution history
- **📊 Monitoring**: Health checks, logging, and performance metrics
- **🔒 Security**: Path validation, input sanitization, and configurable access controls
- **⚡ High Performance**: Async/await throughout, connection pooling, caching
- **🐳 Docker Ready**: Complete containerization with Docker Compose
- **📖 API Documentation**: Interactive OpenAPI docs with FastAPI

## Architecture

```
mcp_server/
├── config.py           # Configuration management
├── server.py            # FastAPI server with MCP endpoints
├── database/            # Database models and connection management
├── llm/                 # LLM client with multi-provider support
├── tools/               # Tool system with extensible base classes
└── utils/               # Logging and utility functions
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and setup
git clone <repository-url>
cd mcp-server

# Start with Docker Compose
docker-compose up -d

# Check health
curl http://localhost:8080/health
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Setup database (PostgreSQL required)
createdb mcp_server

# Run server
python main.py
```

## Configuration

The server uses environment variables for configuration. See `.env.example` for all options:

### Key Settings

```bash
# Server
MCP_HOST=0.0.0.0
MCP_PORT=8080

# Database
PGHOST=localhost
PGDATABASE=mcp_server
PGUSER=postgres
PGPASSWORD=postgres

# LLM Provider
LLM_DEFAULT_PROVIDER=lmstudio  # lmstudio, ollama, openai
LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Security
MCP_FS_ALLOWED_PATHS=["/workspace", "/tmp"]
```

## API Usage

### MCP Protocol (JSON-RPC)

```bash
# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": "1"
  }'

# Call a tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "readfile",
      "arguments": {
        "file_path": "/workspace/example.txt"
      }
    },
    "id": "2"
  }'
```

### REST API (Alternative)

```bash
# List tools
curl http://localhost:8080/api/v1/tools

# Call tool
curl -X POST http://localhost:8080/api/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "readfile",
    "parameters": {
      "file_path": "/workspace/example.txt"
    }
  }'

# LLM completion
curl -X POST http://localhost:8080/api/v1/llm/complete \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

## Available Tools

### Filesystem Tools

- **`readfile`**: Read file contents with encoding support
- **`writefile`**: Write content to files with directory creation
- **`listdirectory`**: List directory contents (with recursive option)
- **`createdirectory`**: Create directories with parent support
- **`deletefile`**: Delete files and directories safely

### Tool Parameters

Each tool has detailed parameter schemas available via the API. Example:

```json
{
  "name": "readfile",
  "description": "Read the contents of a file",
  "parameters": {
    "type": "object",
    "properties": {
      "file_path": {
        "type": "string",
        "description": "Path to the file to read"
      },
      "encoding": {
        "type": "string",
        "description": "File encoding (default: utf-8)",
        "default": "utf-8"
      }
    },
    "required": ["file_path"]
  }
}
```

## LLM Integration

### Supported Providers

#### LM Studio
```bash
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=your-model-name
```

#### Ollama
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

#### OpenAI
```bash
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4
```

### Usage Example

```python
# The server automatically routes to the configured provider
response = await llm_client.complete([
    {"role": "user", "content": "Explain async programming"}
])
```

## Security Features

- **Path Validation**: All file operations are restricted to allowed paths
- **Input Sanitization**: Parameter validation and type checking
- **Size Limits**: Configurable limits for file sizes and requests
- **Error Handling**: Graceful error handling without exposing internals
- **Non-root Execution**: Docker containers run as non-root user

## Monitoring & Logging

### Health Checks

```bash
curl http://localhost:8080/health
```

Returns comprehensive health status:
```json
{
  "status": "healthy",
  "components": {
    "database": {"status": "healthy", "response_time_ms": 12},
    "llm": {"status": "healthy", "providers": {...}},
    "tools": {"status": "healthy", "available_tools": [...]}
  }
}
```

### Logging

- **Structured JSON logging** in production
- **Colored text logging** in development  
- **Request/response logging** with timing
- **Database query logging** for debugging
- **Error tracking** with context

### Metrics

The server tracks:
- Tool execution times and success rates
- LLM response times and token usage  
- Database query performance
- Session activity and retention

## Development

### Adding New Tools

1. Create a new tool class inheriting from `MCPTool`:

```python
from mcp_server.tools.base import MCPTool, ToolParameter, ToolResult

class MyTool(MCPTool):
    @property
    def description(self) -> str:
        return "Description of what this tool does"
    
    @property  
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="param1", 
                type="string",
                description="Parameter description",
                required=True
            )
        ]
    
    async def execute(self, param1: str) -> ToolResult:
        # Tool implementation
        return ToolResult(
            success=True,
            data={"result": "success"}
        )
```

2. Register the tool:

```python
from mcp_server.tools.base import register_tool
register_tool(MyTool())
```

### Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=mcp_server --cov-report=html

# Test specific components
pytest tests/test_tools.py -v
```

### Code Quality

```bash
# Format code
black mcp_server/ tests/

# Lint code  
flake8 mcp_server/ tests/

# Type checking
mypy mcp_server/
```

## Production Deployment

### Environment Setup

1. Use strong database credentials
2. Configure allowed paths restrictively
3. Enable authentication if needed
4. Set up proper logging aggregation
5. Configure rate limiting for public APIs

### Docker Production

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  mcp_server:
    image: mcp-server:latest
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - MCP_ENABLE_AUTH=true
      - MCP_JWT_SECRET_KEY=your-secret-key
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

### Health Monitoring

Set up monitoring for:
- `/health` endpoint availability
- Database connection health
- LLM provider availability  
- Tool execution success rates
- Memory and CPU usage

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify credentials
psql -h localhost -U postgres -d mcp_server
```

**LLM Provider Issues**
```bash
# Test LM Studio
curl http://localhost:1234/v1/models

# Test Ollama
curl http://localhost:11434/api/tags
```

**Permission Errors**
- Verify allowed paths in configuration
- Check file system permissions
- Ensure Docker volume mounts are correct

### Logs

Check logs for detailed error information:
```bash
# Docker logs
docker-compose logs mcp_server

# Local logs
tail -f logs/mcp_server.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the coding standards (see `.cursorrules`)
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

## License

MIT License - see LICENSE file for details. 