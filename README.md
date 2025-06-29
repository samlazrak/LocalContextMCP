# MCP Server with PostgreSQL and LM Studio

A Model Context Protocol (MCP) server implementation that uses PostgreSQL for persistent storage and LM Studio for embeddings, designed to increase context for large language models.

## Features

- **PostgreSQL Backend**: Persistent storage with connection pooling
- **LM Studio Integration**: Uses Qwen2.5 models for embeddings
- **Context Chunking**: Intelligent text chunking with metadata
- **Semantic Search**: Vector similarity search for context retrieval
- **RESTful API**: OpenAPI/Swagger documented endpoints
- **Docker Support**: Complete containerization with docker-compose
- **Comprehensive Testing**: pytest-based test suite

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the project:**
   ```bash
   cd LocalContextMCP
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

3. **Access the API:**
   - API: http://localhost:5000
   - Swagger Docs: http://localhost:5000/apidocs
   - PostgreSQL: localhost:5432

### Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL:**
   - Create database: `mcp_memory`
   - Set environment variables (see Configuration section)
   - Run schema setup: `python db.py`

3. **Start the server:**
   ```bash
   python api_server.py
   ```

## Configuration

### Environment Variables

```bash
# PostgreSQL Configuration
PGHOST=localhost
PGPORT=5432
PGDATABASE=mcp_memory
PGUSER=postgres
PGPASSWORD=your_password

# LM Studio Configuration
LMSTUDIO_API_BASE=http://localhost:1234/v1
LMSTUDIO_EMBEDDING_MODEL=qwen2.5-coder-0.5B-instruct
```

## API Endpoints

### Health Check
```http
GET /health
```

### Store Message
```http
POST /message
Content-Type: application/json

{
  "user_id": "user123",
  "session_id": "session456",
  "role": "user",
  "content": "Hello, world!"
}
```

### Store Context Chunk
```http
POST /context_chunk
Content-Type: application/json

{
  "session_id": "session456",
  "chunk_index": 0,
  "content": "Chunk content",
  "embedding": [0.1, 0.2, ...],
  "message_id": 1,
  "start_offset": 0,
  "end_offset": 12
}
```

### Retrieve Recent Chunks
```http
GET /recent_chunks?session_id=session456&limit=5
```

### Semantic Search
```http
POST /semantic_search
Content-Type: application/json

{
  "session_id": "session456",
  "query": "search query",
  "top_k": 3
}
```

## Development

### Project Structure
```
LocalContextMCP/
├── api_server.py          # Flask API server
├── db.py                  # Database connection and setup
├── embedding.py           # LM Studio embedding generation
├── chunking.py            # Text chunking logic
├── store_and_retrieve.py  # Database operations
├── semantic_search.py     # Vector similarity search
├── schema.sql            # PostgreSQL schema
├── requirements.txt      # Python dependencies
├── tests/                # Test suite
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Multi-service setup
└── .cursor/             # Cursor IDE configuration
```

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html -v
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .
```

## Docker Commands

```bash
# Build image
docker build -t mcp-server .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## Database Schema

### Tables
- **messages**: Chat messages with user and session info
- **context_chunks**: Text chunks with embeddings and metadata
- **users**: User information
- **schema_version**: Database schema versioning

### Indexes
- `idx_context_chunks_session_chunk`: Fast chunk retrieval by session
- `idx_context_chunks_message_id`: Link chunks to messages
- `idx_messages_session_id`: Fast message retrieval by session

## LM Studio Setup

1. **Install LM Studio** on your machine
2. **Load Qwen2.5 models**:
   - `qwen2.5-coder-0.5B-instruct` (for embeddings)
   - `qwen2.5-coder-14B-instruct` (for primary LLM)
3. **Start the server** on port 1234
4. **Configure the API base URL** in environment variables

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify environment variables
   - Ensure database exists

2. **LM Studio Connection Failed**
   - Verify LM Studio is running on port 1234
   - Check model is loaded
   - Test API endpoint manually

3. **Docker Issues**
   - Check Docker and docker-compose are installed
   - Ensure ports 5000 and 5432 are available
   - Check container logs: `docker-compose logs`

### Logs
- Application logs are available in the console
- Docker logs: `docker-compose logs -f app`
- Database logs: `docker-compose logs -f db`

## Contributing

1. Follow the coding standards in `.cursorrules`
2. Write tests for new features
3. Update documentation
4. Use the provided development tools

## License

This project is licensed under the MIT License. 