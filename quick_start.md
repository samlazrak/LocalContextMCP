# 🚀 Quick Start Guide - Comprehensive MCP Server

Get your Void IDE supercharged with all the MCP servers that make Cursor amazing - in just 5 minutes!

## ⚡ 1-Minute Setup (Docker)

```bash
# Clone the repository
git clone <repo-url>
cd LocalContextMCP

# Set your API keys
echo "DEEPSEEK_API_KEY=your_key_here" > .env
echo "POSTGRES_PASSWORD=secure_password" >> .env

# Start everything with Docker
docker-compose -f docker-compose.comprehensive.yml up -d

# Wait 2 minutes for services to initialize, then test
curl http://localhost:8080/health
```

✅ **Done!** Your comprehensive MCP server is running at `http://localhost:8080`

## ⚡ 5-Minute Manual Setup

### Step 1: Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js MCP servers
npm install -g @modelcontextprotocol/server-github
npm install -g @modelcontextprotocol/server-sqlite
```

### Step 2: Setup Local AI Model
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Granite 3.1 8B (local AI model)
ollama pull granite3.1:8b
```

### Step 3: Setup Database
```bash
# Create database
createdb comprehensive_mcp

# Database schema is auto-initialized
```

### Step 4: Configure Environment
```bash
# Copy and edit environment file
cp .env.example .env

# Add your DeepSeek API key
export DEEPSEEK_API_KEY="your_deepseek_api_key"
```

### Step 5: Start Server
```bash
# Start everything
./start_comprehensive_mcp.sh
```

## 🧪 Verify Setup

Test that everything is working:

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

## 🔧 Configure Void IDE

Add this to your Void IDE configuration:

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

## ⚙️ Essential Environment Variables

**Minimum required:**
```bash
DEEPSEEK_API_KEY=your_deepseek_api_key  # For AI features
POSTGRES_PASSWORD=your_password         # For database
```

**Optional but recommended:**
```bash
GITHUB_TOKEN=your_github_token          # For GitHub integration
OPENAI_API_KEY=your_openai_key         # For OpenAI features
HUGGINGFACE_TOKEN=your_hf_token        # For HuggingFace models
```

## 🎯 What You Get

### 🤖 Dual AI Models
- **DeepSeek-Coder-v2-lite-instruct**: Complex analysis, debugging, generation
- **Granite 3.1 8B**: Fast local completions and basic tasks

### 🛠️ 30+ Integrated MCP Servers
- **Development**: filesystem, git, github, docker, kubernetes
- **Databases**: postgres, sqlite, mysql, redis
- **Web Tools**: web-search, fetch, puppeteer
- **Code Quality**: eslint, black, prettier  
- **Testing**: pytest, jest
- **AI/ML**: huggingface, openai
- **Productivity**: notion, slack, google-drive
- **Security**: sentry, monitoring

### 🚀 Advanced Features
- **Smart Code Completion**: Multi-source, context-aware
- **Project Analysis**: Deep architectural insights
- **AI Debugging**: Intelligent error analysis and fixes
- **Code Generation**: Context-aware code creation
- **Real-time Monitoring**: File watching and change detection
- **Persistent Memory**: Context retention across sessions

## 📊 Quick Health Check

```bash
# Server status
curl http://localhost:8080/health | jq

# List all MCP servers
curl http://localhost:8080/api/servers | jq

# Test code completion
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools_list",
    "id": 1
  }' | jq
```

## 🐛 Quick Troubleshooting

### Server won't start?
```bash
# Check logs
tail -f comprehensive_mcp.log

# Check dependencies
pip check && node --version && psql --version
```

### Can't connect to AI models?
```bash
# Test DeepSeek API
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     https://api.deepseek.com/v1/models

# Test Ollama (local)
curl http://localhost:11434/api/tags
```

### Database issues?
```bash
# Test connection
psql -h localhost -U postgres -d comprehensive_mcp -c "SELECT 1;"

# Check if running
ps aux | grep postgres
```

## 🎉 Next Steps

1. **Configure Void IDE** with the provided config
2. **Open a project** in Void IDE
3. **Try code completion** - just start typing!
4. **Ask for debugging help** on any error
5. **Generate code** by describing what you want
6. **Explore tools** with the `/api/servers` endpoint

## 📚 Learn More

- **Full Documentation**: [COMPREHENSIVE_README.md](COMPREHENSIVE_README.md)
- **API Reference**: Browse `/api/servers` endpoint  
- **Troubleshooting**: Check the logs and health endpoints
- **Customization**: Edit `comprehensive_mcp_server.py`

---

**🚀 You're all set!** You now have the most comprehensive MCP server running, giving your Void IDE the same powerful features that make Cursor amazing. Happy coding! 🎯