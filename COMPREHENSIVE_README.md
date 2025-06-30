# Comprehensive MCP Meta-Server for Void IDE

A powerful Model Context Protocol (MCP) meta-server that aggregates all useful local MCP servers into one unified system, designed specifically for Void IDE integration. This server provides the complete toolkit that makes Cursor such a powerful IDE, now available for Void.

## 🎯 Overview

This comprehensive MCP server acts as a central hub that:
- **Aggregates 30+ essential MCP servers** into one unified interface
- **Dual AI model support**: DeepSeek-Coder-v2-lite-instruct (remote) + Granite 3.1 8B (local)
- **Provides advanced IDE features**: Code completion, debugging, analysis, generation
- **Full project context awareness** with persistent memory
- **Seamless Void IDE integration** via HTTP/JSON-RPC

## 🚀 Key Features

### AI Models
- **DeepSeek-Coder-v2-lite-instruct**: Remote processing for complex tasks
- **Granite 3.1 8B**: Local model for fast completions and basic analysis
- **Intelligent routing**: Automatically selects the best model for each task

### Integrated MCP Servers
- **Development**: filesystem, git, github, docker, kubernetes
- **Databases**: postgres, sqlite, mysql, redis, mongodb
- **Web & Search**: web-search, fetch, puppeteer, browser automation
- **Code Quality**: eslint, black, prettier, linting tools
- **Testing**: pytest, jest, automated testing frameworks
- **AI/ML**: huggingface, openai, model integration
- **Productivity**: notion, google-drive, slack, discord
- **Security**: sentry, monitoring, error tracking

### Advanced Capabilities
- **Comprehensive Code Completion**: Multi-source intelligent completions
- **Project Analysis**: Deep architectural insights with AI
- **AI-Assisted Debugging**: Smart error analysis and fixes
- **Code Generation**: Context-aware code creation
- **Multi-Language Support**: Python, JavaScript, TypeScript, Go, Rust, and more
- **Real-time File Watching**: Project changes monitoring
- **Persistent Memory**: Context retention across sessions

## 📋 Prerequisites

- **Python 3.8+**
- **PostgreSQL 12+**
- **Node.js 18+** (for MCP servers)
- **Docker** (optional, for containerized servers)
- **API Keys**: DeepSeek API key for remote AI processing

## 🛠 Quick Setup

### 1. Automated Setup
```bash
# Clone and setup everything automatically
git clone <repository>
cd LocalContextMCP
chmod +x setup_comprehensive_mcp.sh
./setup_comprehensive_mcp.sh
```

### 2. Manual Setup

#### Install Dependencies
```bash
pip install -r requirements.txt
npm install -g @modelcontextprotocol/server-github
npm install -g @modelcontextprotocol/server-sqlite
# ... (see setup script for full list)
```

#### Setup Database
```bash
createdb comprehensive_mcp
# Database schema is initialized automatically
```

#### Install Local AI Model
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
# Pull Granite 3.1 8B
ollama pull granite3.1:8b
```

#### Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

### 3. Start the Server
```bash
./start_comprehensive_mcp.sh
```

## ⚙️ Configuration

### Environment Variables
```bash
# LLM Configuration
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_API_KEY=your_deepseek_api_key
GRANITE_API_BASE=http://localhost:11434/v1

# Database Configuration
PGHOST=localhost
PGPORT=5432
PGDATABASE=comprehensive_mcp
PGUSER=postgres
PGPASSWORD=your_password

# Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=8080
DEBUG=false
```

### Void IDE Integration
Use the provided `void_mcp_config.json`:
```json
{
  "mcp": {
    "servers": {
      "comprehensive": {
        "endpoint": "http://localhost:8080",
        "protocol": "http",
        "capabilities": [
          "code_completion",
          "project_analysis",
          "debugging",
          "code_generation"
        ]
      }
    }
  }
}
```

## 🔧 API Endpoints

### Health & Status
- `GET /health` - Server health and component status
- `GET /api/servers` - List all MCP servers and their status

### Core MCP Methods
- `comprehensive_code_completion` - Advanced multi-source code completion
- `project_analysis` - Deep project analysis with AI insights
- `ai_assisted_debugging` - Smart debugging assistance
- `code_generation` - Context-aware code generation
- `tools_list` - List all available tools from all servers

### Example Usage
```python
import aiohttp
import json

async def get_completion():
    payload = {
        "jsonrpc": "2.0",
        "method": "comprehensive_code_completion",
        "params": {
            "file_path": "/path/to/file.py",
            "line": 10,
            "column": 5,
            "context": "def process_data():",
            "project_path": "/path/to/project",
            "language": "python"
        },
        "id": 1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8080", json=payload) as response:
            result = await response.json()
            completions = result["result"]["completions"]
            return completions
```

## 🧪 Testing

Test the server functionality:
```bash
python3 test_comprehensive_mcp.py
```

Expected output:
```
🧪 Testing Comprehensive MCP Server...
✅ Health check passed
✅ Found 30+ MCP servers
✅ Found 100+ total tools
🎉 Test completed!
```

## 🐳 Docker Deployment

### Using Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker
```bash
# Build image
docker build -t comprehensive-mcp .

# Run container
docker run -d \
  -p 8080:8080 \
  -e DEEPSEEK_API_KEY=your_key \
  -e PGPASSWORD=your_password \
  comprehensive-mcp
```

## 📊 Monitoring & Observability

### Health Monitoring
```bash
# Check server health
curl http://localhost:8080/health

# Monitor MCP servers status
curl http://localhost:8080/api/servers
```

### Logs
- Application logs: `comprehensive_mcp.log`
- Database queries logged with timing
- Tool call metrics and performance data

### Performance Metrics
The server tracks:
- Tool call latency
- AI model response times
- Database query performance
- Memory usage per session

## 🔍 Troubleshooting

### Common Issues

#### Server Won't Start
```bash
# Check dependencies
pip check
node --version
psql --version

# Check logs
tail -f comprehensive_mcp.log
```

#### DeepSeek API Issues
```bash
# Test API connectivity
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     https://api.deepseek.com/v1/models
```

#### Local Model Issues
```bash
# Check Ollama status
ollama list
ollama ps

# Restart Ollama
sudo systemctl restart ollama
```

#### Database Connection Issues
```bash
# Test database connection
psql -h localhost -U postgres -d comprehensive_mcp -c "SELECT 1;"

# Check database logs
sudo journalctl -u postgresql
```

### Performance Optimization

#### For Large Projects
- Enable deep analysis caching
- Increase database connection pool size
- Use SSD storage for better I/O

#### For Remote Deployments
- Configure proper firewall rules
- Use HTTPS with SSL certificates
- Enable authentication middleware

## 🛡️ Security Considerations

### API Keys
- Store API keys in environment variables
- Never commit keys to version control
- Rotate keys regularly

### Database Security
- Use strong PostgreSQL passwords
- Enable SSL connections in production
- Regular database backups

### Network Security
- Configure firewall rules
- Use HTTPS in production
- Implement rate limiting

## 🤝 Contributing

### Adding New MCP Servers
1. Add server config to `mcp_server_configs`
2. Install server dependencies
3. Update documentation
4. Test integration

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black .
flake8 .
```

## 📚 Architecture

### Core Components
```
┌─────────────────────────────────────────┐
│            Void IDE                     │
├─────────────────────────────────────────┤
│      Comprehensive MCP Server           │
├─────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────┐   │
│  │ DeepSeek    │  │ Granite 3.1 8B  │   │
│  │ (Remote)    │  │ (Local)         │   │
│  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────┤
│           MCP Server Registry           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │   Git   │ │Database │ │Web Tools│   │
│  └─────────┘ └─────────┘ └─────────┘   │
├─────────────────────────────────────────┤
│         PostgreSQL Database             │
└─────────────────────────────────────────┘
```

### Data Flow
1. **Void IDE** sends requests via HTTP/JSON-RPC
2. **Comprehensive MCP Server** routes to appropriate components
3. **AI Models** provide intelligent responses
4. **MCP Servers** handle specific tool operations
5. **Database** maintains session state and cache

## 📈 Roadmap

### Upcoming Features
- [ ] **Multi-tenant support** for team environments
- [ ] **Custom model fine-tuning** on project data
- [ ] **Advanced caching strategies** for better performance
- [ ] **Real-time collaboration** features
- [ ] **Plugin system** for custom MCP servers
- [ ] **Web dashboard** for server management
- [ ] **Metrics and analytics** dashboard

### Integration Plans
- [ ] **VS Code extension** compatibility
- [ ] **JetBrains IDE** plugin
- [ ] **Vim/Neovim** integration
- [ ] **Emacs** package
- [ ] **API gateway** for microservices

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Anthropic** for the Model Context Protocol
- **DeepSeek** for the excellent coding model
- **IBM** for Granite models
- **Cursor** for inspiration on IDE AI integration
- **Community MCP servers** for extensive tooling

## 📞 Support

- **Documentation**: Check this README and inline comments
- **Issues**: Use GitHub Issues for bug reports
- **Discussions**: Use GitHub Discussions for questions
- **Email**: [Your contact email]

---

**Built with ❤️ for the developer community**

Transform your Void IDE into an AI-powered development environment with the comprehensive MCP server that brings together the best tools in the ecosystem!