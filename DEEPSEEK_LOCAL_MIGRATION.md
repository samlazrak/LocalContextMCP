# 🔄 DeepSeek Local Migration Guide

## Overview
This document outlines the migration from DeepSeek API-based authentication to local DeepSeek server setup. The changes eliminate the need for API keys and enable fully local AI processing.

## 🔧 Changes Made

### 1. Server Configuration Updates

#### `comprehensive_mcp_server.py`
- **LLM Config**: Changed DeepSeek from remote to local
  - `endpoint`: `https://api.deepseek.com/v1` → `http://localhost:8000/v1`
  - `api_key`: Required → `None` (removed)
  - `type`: `remote` → `local`
- **Client Initialization**: Removed API key headers and Bearer token authentication
- **Health Check**: Updated to show "connected (local)" status

#### Environment Configuration
- **`.env` / `env.example`**: Added local DeepSeek configuration
  ```bash
  # Old (API-based)
  DEEPSEEK_API_BASE=https://api.deepseek.com/v1
  DEEPSEEK_API_KEY=your_deepseek_api_key
  
  # New (Local)
  DEEPSEEK_API_BASE=http://localhost:8000/v1
  DEEPSEEK_MODEL=deepseek-coder
  ```

#### Docker Configuration
- **`docker-compose.comprehensive.yml`**: Updated to use `host.docker.internal:8000`
- **`comprehensive_mcp_config.json`**: Removed API key requirement, added local service documentation

### 2. Installation Scripts

#### `setup_comprehensive_mcp.sh`
- Removed DeepSeek API key prompts
- Added local DeepSeek setup instructions
- Updated final output to reflect local setup

#### New: `scripts/setup_local_deepseek.sh`
- Interactive setup script with 5 options:
  1. **Ollama** (Recommended - Easy setup)
  2. **vLLM** (High performance)
  3. **Text Generation WebUI** (User-friendly interface)
  4. **Docker with TGI** (Hugging Face Text Generation Inference)
  5. **Skip DeepSeek** (use only Granite)

### 3. Documentation Updates

#### `docs/quick_start.md`
- Complete rewrite focusing on local setup
- Added local LLM model documentation
- Updated troubleshooting for local services
- Removed API key instructions

## 🚀 Migration Steps

### For Existing Users

1. **Update Environment**:
   ```bash
   # Edit your .env file
   sed -i 's|DEEPSEEK_API_BASE=.*|DEEPSEEK_API_BASE=http://localhost:8000/v1|' .env
   sed -i '/DEEPSEEK_API_KEY/d' .env
   echo "DEEPSEEK_MODEL=deepseek-coder" >> .env
   ```

2. **Set up Local DeepSeek**:
   ```bash
   # Run the interactive setup script
   ./scripts/setup_local_deepseek.sh
   ```

3. **Update Server Code**:
   - The server code is already updated to handle local connections
   - No API key authentication required
   - Automatic fallback to Granite if DeepSeek unavailable

### For New Users

1. **Clone and Install**:
   ```bash
   git clone <repository-url>
   cd LocalContextMCP
   pip install -r requirements.txt
   ```

2. **Setup Local DeepSeek**:
   ```bash
   ./scripts/setup_local_deepseek.sh
   ```

3. **Start Services**:
   ```bash
   # Terminal 1: Start DeepSeek
   ./start_deepseek_ollama.sh  # or your chosen method
   
   # Terminal 2: Start Granite
   ollama serve
   
   # Terminal 3: Start MCP Server
   python comprehensive_mcp_server.py
   ```

## 🏗️ Local DeepSeek Setup Options

### Option 1: Ollama (Recommended)
```bash
# Install and setup
ollama pull deepseek-coder:6.7b
export OLLAMA_HOST=0.0.0.0:8000
ollama serve
```

**Pros**: Easy setup, integrated model management
**Cons**: Limited to available Ollama models

### Option 2: vLLM (High Performance)
```bash
# Install and run
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/deepseek-coder-6.7b-instruct \
    --host 0.0.0.0 --port 8000
```

**Pros**: High performance, GPU acceleration, production-ready
**Cons**: More complex setup, higher resource requirements

### Option 3: Text Generation WebUI
```bash
# Clone and setup
git clone https://github.com/oobabooga/text-generation-webui.git
cd text-generation-webui
python server.py --api --api-port 8000 \
    --model deepseek-ai/deepseek-coder-6.7b-instruct
```

**Pros**: User-friendly interface, lots of options
**Cons**: More overhead, web interface may be unnecessary

### Option 4: Docker with TGI
```bash
# Using docker-compose
docker-compose -f docker-compose.deepseek.yml up -d
```

**Pros**: Isolated environment, easy deployment
**Cons**: Docker overhead, requires container management

### Option 5: Skip DeepSeek
- Uses only Granite 3.1 8B for all AI tasks
- Lighter resource usage
- Reduced functionality for complex tasks

## 🔍 Verification

### Test Local DeepSeek Connection
```bash
# Test the API endpoint
curl -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "deepseek-coder",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

### Test MCP Server Integration
```bash
# Health check
curl http://localhost:8080/health

# Should show "deepseek_llm": "connected (local)"
```

### Test AI Features
```bash
# Test code completion
curl -X POST http://localhost:8080/ \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "method": "comprehensive_code_completion",
    "params": {
      "file_path": "test.py",
      "line": 1,
      "column": 1,
      "context": "def hello",
      "project_path": "."
    },
    "id": 1
  }'
```

## 🎯 Benefits of Local Setup

### Security & Privacy
- **No API Keys**: No external authentication required
- **Local Processing**: All data stays on your machine
- **No Rate Limits**: Process as much as your hardware allows

### Performance
- **No Network Latency**: Direct local connections
- **Consistent Performance**: Not dependent on external service availability
- **Custom Models**: Use any DeepSeek-compatible model

### Cost & Control
- **No Usage Fees**: No per-token or per-request charges
- **Full Control**: Customize model parameters and behavior
- **Offline Capable**: Works without internet connection

## 🚨 Troubleshooting

### Common Issues

#### "DeepSeek connection failed"
1. Check if DeepSeek is running: `curl http://localhost:8000/v1/models`
2. Verify port not in use: `lsof -i :8000`
3. Check logs for startup errors

#### "Model not found"
1. Ensure model is downloaded and available
2. Check model name in configuration
3. Verify model path/name matches server setup

#### "Out of memory"
1. DeepSeek models require significant RAM (6GB+ for 6.7B model)
2. Consider using quantized models
3. Adjust model parameters for your hardware

#### "Slow performance"
1. Enable GPU acceleration if available
2. Use quantized models for faster inference
3. Adjust batch size and context length

### Performance Optimization

#### Hardware Recommendations
- **RAM**: 16GB+ (8GB minimum)
- **Storage**: SSD for model storage
- **GPU**: CUDA-compatible GPU for acceleration (optional)
- **CPU**: Multi-core processor for parallel processing

#### Model Optimization
- Use quantized models (4-bit, 8-bit) for lower memory usage
- Adjust context window size based on needs
- Use smaller models for simpler tasks

## 📋 Migration Checklist

- [ ] Update environment variables
- [ ] Remove API key references
- [ ] Set up local DeepSeek server
- [ ] Test local connections
- [ ] Verify MCP server integration
- [ ] Update IDE configuration
- [ ] Test AI features
- [ ] Document local setup for team

## 🔮 Future Enhancements

1. **Multi-Model Support**: Easy switching between different local models
2. **Auto-Discovery**: Automatic detection of running model servers
3. **Load Balancing**: Distribute requests across multiple model instances
4. **Model Management**: Built-in model download and management tools
5. **Performance Monitoring**: Track model performance and resource usage

---

**✅ Migration Complete**: Your LocalContextMCP setup now runs entirely locally with no external API dependencies!