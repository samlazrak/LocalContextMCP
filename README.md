# LocalContextMCP

A smart Model Context Protocol server that gives your language models a memory. Built with PostgreSQL for persistence and LM Studio for embeddings, because context matters.

## What This Does

Ever wished your LLM could remember things from earlier in long conversations? This server solves that by storing conversation chunks with semantic embeddings, letting you retrieve relevant context when you need it.

The magic happens through:
- **PostgreSQL storage** - Your conversations persist between sessions
- **LM Studio embeddings** - Using Qwen2.5 models to understand meaning
- **Smart chunking** - Breaks text into meaningful pieces with metadata
- **Semantic search** - Finds relevant context based on meaning, not just keywords
- **Clean REST API** - Easy to integrate with any application

## Getting Started

### The Easy Way (Docker)

If you have Docker installed, you're 30 seconds away from running this:

```bash
git clone <your-repo-url>
cd LocalContextMCP
docker-compose up -d
```

That's it! The API will be running at http://localhost:5000 and you can check out the interactive docs at http://localhost:5000/apidocs.

### The Manual Way

Rather build things yourself? Cool, here's how:

1. **Get your environment ready:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL:**
   You'll need a PostgreSQL database called `mcp_memory`. Create it however you normally do, then run:
   ```bash
   python db.py
   ```

3. **Fire it up:**
   ```bash
   python api_server.py
   ```

## Configuration

You'll need these environment variables set up:

```bash
# PostgreSQL - adjust these for your setup
PGHOST=localhost
PGPORT=5432
PGDATABASE=mcp_memory
PGUSER=postgres
PGPASSWORD=your_password

# LM Studio - assuming you're running locally
LMSTUDIO_API_BASE=http://localhost:1234/v1
LMSTUDIO_EMBEDDING_MODEL=qwen2.5-coder-0.5B-instruct
```

## How to Use It

### Check if everything's working
```bash
curl http://localhost:5000/health
```

### Store a message
```bash
curl -X POST http://localhost:5000/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "session_id": "chat_001", 
    "role": "user",
    "content": "I love building with Python and PostgreSQL"
  }'
```

### Search for relevant context
```bash
curl -X POST http://localhost:5000/semantic_search \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "chat_001",
    "query": "python development",
    "top_k": 3
  }'
```

There are more endpoints - check the Swagger docs at `/apidocs` for the full list.

## Setting Up LM Studio

You'll need LM Studio running to generate embeddings:

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Load these models:
   - `qwen2.5-coder-0.5B-instruct` for embeddings
   - `qwen2.5-coder-14B-instruct` for your main LLM (optional)
3. Start the local server (usually runs on port 1234)

## Development

### Project Layout
```
LocalContextMCP/
├── api_server.py          # Main Flask API
├── db.py                  # Database setup and connections
├── embedding.py           # LM Studio integration
├── chunking.py            # Text processing
├── store_and_retrieve.py  # Database operations
├── semantic_search.py     # Vector search
├── schema.sql            # Database schema
├── tests/                # Test suite
└── docker-compose.yml    # Easy deployment
```

### Running Tests
```bash
pytest tests/ -v
```

### Code Formatting
```bash
black . && flake8 .
```

## When Things Go Wrong

**Can't connect to PostgreSQL?**
- Make sure it's running (`sudo systemctl status postgresql`)
- Check your environment variables
- Verify the database exists

**LM Studio not responding?**
- Check if it's running on port 1234
- Make sure you have a model loaded
- Try hitting the API directly: `curl http://localhost:1234/v1/models`

**Docker acting up?**
- Make sure ports 5000 and 5432 aren't already in use
- Check the logs: `docker-compose logs`
- Try rebuilding: `docker-compose up -d --build`

## Contributing

Found a bug or want to add a feature? Great! Just:
1. Follow the coding standards in `.cursorrules`
2. Add tests for your changes
3. Update the docs if needed

## Why This Exists

Large language models are amazing but they forget everything between conversations. This project gives them a memory by storing conversation context with semantic embeddings, making it easy to retrieve relevant information when needed. It's like giving your AI a notebook it can search through.

## License

MIT License - use it however you want! 