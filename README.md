# MCP Server – persistent context & semantic search for your LLM apps

Hey there! 👋  This project started as a weekend experiment to give large-language-model agents a real memory.  It has since grown into a small but mighty JSON-RPC / REST service that stores chat history in Postgres, lets you chunk long documents, and serves up relevant context via fast vector search.

If you are building agents, chatbots, or IDE extensions and you keep hitting the context-window wall, this repository is for you.

---

## What you get

• **PostgreSQL storage** – all messages and chunks land in a proper database with connection pooling.
• **Embeddings via LM Studio** – drop-in local embedding generation (defaults to Qwen2.5 but you can swap in your own).
• **Semantic search** – PostgreSQL + pgvector under the hood for lightning-fast similarity queries.
• **Plain JSON-RPC & REST APIs** – call it from any language or curl.
• **Docker-first workflow** – one command and you are up and running.
• **Tests included** – pytest covers the critical paths so you can hack without fear.

---

## Quick start (2 mins)

The easiest way is Docker Compose – it spins up Postgres **and** the server.

```bash
# 1.  Grab the code
$ git clone https://github.com/your-org/LocalContextMCP.git
$ cd LocalContextMCP

# 2.  Add a couple of secrets (copy the template for convenience)
$ cp env.example .env
$ echo "PGPASSWORD=postgres" >> .env  # change me in prod!

# 3.  Fire it up
$ docker-compose up ‑d
```

Once the containers say **healthy** you should see:

* API root: http://localhost:8080  
* Swagger / Redoc: http://localhost:8080/apidocs  
* Postgres: `localhost:5432` (db: `mcp_memory`)

Run a smoke test:

```bash
$ curl -s http://localhost:8080/health | jq
```

You should get a neat little JSON payload with `"status": "healthy"`.

---

## Running without Docker

1. Python 3.11+ virtualenv:
   ```bash
   pip install -r requirements.txt
   ```
2. Make sure Postgres is running and the credentials in `.env` (or your shell) are correct.
3. Kick off the server:
   ```bash
   python mcp_server.py  # or integrated_mcp_server.py if you want the fancy features
   ```

That's it.

---

## Configuration in a nutshell

Everything lives in environment variables.  The important ones:

```
PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD   # Postgres
LMSTUDIO_API_BASE                                     # http://localhost:1234/v1 by default
LMSTUDIO_EMBEDDING_MODEL                              # qwen2.5-coder-0.5B-instruct
```

Check `env.example` for the full list.

---

## API overview

Full OpenAPI docs are served at `/apidocs`, but here are the greatest hits:

• `GET  /health` – simple JSON health check  
• `POST /message` – store a chat message  
• `POST /context_chunk` – add an embedding-ready chunk  
• `GET  /recent_chunks?session_id=xyz&limit=5` – fetch recent history  
• `POST /semantic_search` – return the *k* most similar chunks

All endpoints accept / return JSON.

---

## Hacking & tests

```bash
# run the whole suite
pytest -v

# black + flake8 keep the linter gremlins away
black .
flake8 .
```

Folder layout (trimmed):

```
.
├── mcp_server.py               # basic JSON-RPC & REST server
├── integrated_mcp_server.py    # same but with async goodies and code-intel extras
├── lmstudio_integration.py     # tiny helper around LM Studio's API
├── init.sql                    # schema if you like raw SQL
├── tests/                      # pytest test cases
└── docker-compose.yml          # local orchestration
```

---

## Contributing

Pull requests are welcome!  If you spot a bug or have an idea, open an issue first so we can discuss.  Please remember to:

1. Follow PEP 8 and add type hints.
2. Write or update tests.
3. Keep the docs in sync (including this README).

---

## License

MIT – do what you will, just don't blame us if it breaks. 