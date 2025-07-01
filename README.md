# LocalContextMCP

A powerful Model Context Protocol (MCP) server that provides intelligent code assistance, project analysis, and persistent memory for language models. Built with modern Python, PostgreSQL, and LM Studio integration.

## 🚀 Features

- **Smart Code Intelligence**: Context-aware completions, refactoring, and debugging assistance
- **Persistent Memory**: Store and retrieve conversation context with semantic search
- **Multi-LLM Support**: Integration with LM Studio, DeepSeek, and other local models
- **Project Analysis**: Deep understanding of codebases with symbol extraction and dependency mapping
- **Real-time File Watching**: Automatic updates when files change
- **Extensible Architecture**: Easy to add new tools and capabilities
- **Production Ready**: Docker deployment, health monitoring, and comprehensive logging

## 🏗️ Architecture

```
LocalContextMCP/
├── src/
│   ├── mcp/
│   │   ├── server.py          # Main MCP server
│   │   ├── tools/             # MCP tool implementations
│   │   └── handlers/          # Request handlers
│   ├── core/
│   │   ├── database.py        # Database operations
│   │   ├── llm_client.py      # LLM integrations
│   │   └── config.py          # Configuration management
│   ├── intelligence/
│   │   ├── code_analyzer.py   # Code analysis engine
│   │   ├── project_manager.py # Project-level operations
│   │   └── semantic_search.py # Vector search capabilities
│   └── api/
│       ├── rest_server.py     # REST API endpoints
│       └── middleware/        # Authentication, logging, etc.
├── tests/                     # Comprehensive test suite
├── docker/                    # Docker configuration
├── scripts/                   # Utility scripts
└── docs/                      # Documentation
```

## 🛠️ Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and start
git clone <repository-url>
cd LocalContextMCP
docker-compose up -d

# Verify installation
curl http://localhost:8080/health
```

### Option 2: Manual Installation

```bash
# 1. Install dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Setup PostgreSQL database
createdb localcontextmcp
psql localcontextmcp < database/schema.sql

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Start the server
python -m src.mcp.server
```

## ⚙️ Configuration

Create a `.env` file with your settings:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/localcontextmcp

# LM Studio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=qwen2.5-coder-0.5B-instruct

# DeepSeek (optional)
DEEPSEEK_BASE_URL=http://localhost:8000/v1
DEEPSEEK_MODEL=deepseek-coder

# Server
HOST=0.0.0.0
PORT=8080
LOG_LEVEL=INFO
```

## 🔧 Usage Examples

### MCP JSON-RPC Interface

```bash
# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Get code completions
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "code_completion",
      "arguments": {
        "file_path": "src/main.py",
        "line": 10,
        "column": 5,
        "context": "def hello_world():\n    print("
      }
    },
    "id": 2
  }'
```

### REST API

```bash
# Store a memory
curl -X POST http://localhost:8080/api/memory \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "dev_session_1",
    "content": "Working on authentication system using JWT tokens",
    "metadata": {
      "project": "web_app",
      "topic": "authentication"
    }
  }'

# Search memories
curl -X GET "http://localhost:8080/api/memory/search?query=authentication&limit=5"

# Analyze project
curl -X POST http://localhost:8080/api/project/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/project"}'
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/test_mcp/ -v
pytest tests/test_intelligence/ -v
```

## 📚 Available Tools

### Code Intelligence
- `code_completion`: Context-aware code completions
- `project_analysis`: Deep project structure analysis
- `symbol_search`: Find functions, classes, and variables
- `refactor_suggestions`: AI-powered refactoring recommendations

### Memory & Context
- `store_memory`: Save conversation context
- `search_memory`: Semantic search through stored memories
- `get_context`: Retrieve relevant context for queries

### File Operations
- `read_file`: Secure file reading with access controls
- `write_file`: File writing with backup and validation
- `watch_files`: Real-time file change monitoring

### Development Tools
- `run_tests`: Execute project tests
- `lint_code`: Code quality analysis
- `format_code`: Automatic code formatting
- `git_operations`: Git repository management

## 🔌 LM Studio Setup

1. **Install LM Studio**: Download from [lmstudio.ai](https://lmstudio.ai/)

2. **Download Models**:
   - For embeddings: `qwen2.5-coder-0.5B-instruct`
   - For completions: `qwen2.5-coder-14B-instruct`

3. **Start Server**: Load a model and start the local server (port 1234)

4. **Verify Connection**:
   ```bash
   curl http://localhost:1234/v1/models
   ```

## 🐳 Docker Deployment

The project includes production-ready Docker configuration:

```bash
# Development
docker-compose -f docker/docker-compose.dev.yml up

# Production
docker-compose -f docker/docker-compose.prod.yml up -d

# With monitoring
docker-compose -f docker/docker-compose.monitoring.yml up -d
```

## 🔍 Monitoring & Health

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Logs**: Structured JSON logging with configurable levels
- **Database Monitoring**: Connection pool metrics and query performance

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature-name`
3. **Follow code standards**: Run `black src tests` and `flake8`
4. **Add tests**: Ensure good test coverage
5. **Submit a PR**: Include description and testing notes

## 📋 Development Guidelines

- **Code Style**: Follow PEP 8, use type hints
- **Testing**: Write tests for all new features
- **Documentation**: Update docs for user-facing changes
- **Security**: Validate inputs, use parameterized queries
- **Performance**: Profile database queries, use async where beneficial

## 🐛 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Verify connection
psql -h localhost -U postgres -d localcontextmcp
```

**LM Studio Not Responding**
```bash
# Check if server is running
curl http://localhost:1234/v1/models

# Verify model is loaded in LM Studio interface
```

**Port Already in Use**
```bash
# Find process using port
lsof -i :8080

# Kill process if needed
kill -9 <PID>
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Built on the [Model Context Protocol](https://modelcontextprotocol.io/) specification
- Inspired by the Claude Desktop MCP ecosystem
- Uses [LM Studio](https://lmstudio.ai/) for local LLM inference