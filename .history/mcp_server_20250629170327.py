from flask import Flask, request, jsonify, Response, stream_with_context
from jsonrpcserver import method, dispatch, Success, Error
import os
import subprocess
import sqlite3
import time
import requests
import psycopg2
from bs4 import BeautifulSoup
from urllib.parse import quote
from typing import Dict, Any, Optional
from pydantic import BaseModel
import json
import logging

# --- LM Studio Integration ---
from lmstudio_integration import (
    chat, complete, get_embedding,
    structured_respond_pydantic, structured_respond_jsonschema,
    agentic_act, mcp_tool_call
)

PROJECTS_DIR = "/projects/bot-env"  # Adjust as needed

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- JSON-RPC: LM Studio Endpoints ---

@method
def lmstudio_chat(prompt: str, model_name: Optional[str] = None):
    try:
        result = chat(prompt, model_name)
        logging.info(f"lmstudio_chat: {prompt} -> {result}")
        return Success(result)
    except Exception as e:
        logging.error(f"lmstudio_chat error: {e}")
        return Error(str(e))

@method
def lmstudio_complete(prompt: str, model_name: Optional[str] = None):
    try:
        result = complete(prompt, model_name)
        logging.info(f"lmstudio_complete: {prompt} -> {result}")
        return Success(result)
    except Exception as e:
        logging.error(f"lmstudio_complete error: {e}")
        return Error(str(e))

@method
def lmstudio_embed(text: str, model_name: Optional[str] = None):
    try:
        result = get_embedding(text, model_name)
        logging.info(f"lmstudio_embed: {text} -> {result}")
        return Success(result)
    except Exception as e:
        logging.error(f"lmstudio_embed error: {e}")
        return Error(str(e))

@method
def lmstudio_structured_pydantic(prompt: str, model_name: Optional[str] = None):
    class BookSchema(BaseModel):
        title: str
        author: str
        year: int
    try:
        result = structured_respond_pydantic(prompt, BookSchema, model_name)
        logging.info(f"lmstudio_structured_pydantic: {prompt} -> {result}")
        return Success(result)
    except Exception as e:
        logging.error(f"lmstudio_structured_pydantic error: {e}")
        return Error(str(e))

@method
def lmstudio_structured_jsonschema(prompt: str, schema: dict, model_name: Optional[str] = None):
    try:
        result = structured_respond_jsonschema(prompt, schema, model_name)
        logging.info(f"lmstudio_structured_jsonschema: {prompt} -> {result}")
        return Success(result)
    except Exception as e:
        logging.error(f"lmstudio_structured_jsonschema error: {e}")
        return Error(str(e))

@method
def lmstudio_agentic_act(prompt: str, model_name: Optional[str] = None):
    try:
        # Dynamically register all MCP tools as agentic tools
        # For demo, just use mcp_tool_call
        result = agentic_act(prompt, [mcp_tool_call], model_name)
        logging.info(f"lmstudio_agentic_act: {prompt} -> {result}")
        return Success("Agentic act started (see logs/stream for output)")
    except Exception as e:
        logging.error(f"lmstudio_agentic_act error: {e}")
        return Error(str(e))

# --- REST Endpoints for LM Studio Features ---

@app.route("/lmstudio/chat", methods=["POST"])
def rest_lmstudio_chat():
    data = request.json
    prompt = data.get("prompt")
    model_name = data.get("model_name")
    try:
        result = chat(prompt, model_name)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/lmstudio/complete", methods=["POST"])
def rest_lmstudio_complete():
    data = request.json
    prompt = data.get("prompt")
    model_name = data.get("model_name")
    try:
        result = complete(prompt, model_name)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/lmstudio/embed", methods=["POST"])
def rest_lmstudio_embed():
    data = request.json
    text = data.get("text")
    model_name = data.get("model_name")
    try:ls -la *.py | grep -E "(mcp_server|integrated|enhanced)" | head -10
    ls -la *.py | grep -E "(mcp_server|integrated|enhanced)" | head -10
        result = get_embedding(text, model_name)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/lmstudio/structured_pydantic", methods=["POST"])
def rest_lmstudio_structured_pydantic():
    data = request.json
    prompt = data.get("prompt")
    model_name = data.get("model_name")
    class BookSchema(BaseModel):
        title: str
        author: str
        year: int
    try:
        result = structured_respond_pydantic(prompt, BookSchema, model_name)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/lmstudio/structured_jsonschema", methods=["POST"])
def rest_lmstudio_structured_jsonschema():
    data = request.json
    prompt = data.get("prompt")
    schema = data.get("schema")
    model_name = data.get("model_name")
    try:
        result = structured_respond_jsonschema(prompt, schema, model_name)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/lmstudio/agentic_act", methods=["POST"])
def rest_lmstudio_agentic_act():
    data = request.json
    prompt = data.get("prompt")
    model_name = data.get("model_name")
    try:
        # For demo, just use mcp_tool_call
        def stream():
            yield "Agentic act started\n"
            def on_message(msg):
                return msg + "\n"
            agentic_act(prompt, [mcp_tool_call], model_name, on_message=on_message)
        return Response(stream_with_context(stream()), mimetype="text/plain")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@method
def tools_list():
    return Success([
        "git", "time", "sqlite", "fetch", "sequentialthinking",
        "postgres", "memory", "filesystem", "web-search", "localContextMCP",
        "desktop-commander", "duckduckgo-mcp-server", "servers", "mcp-server-sqlite-npx"
    ])

@method
def tools_call(tool, params=None):
    params = params or {}
    if tool == "git":
        cmd = params.get("command", "status")
        try:
            result = subprocess.check_output(["git"] + cmd.split(), cwd=PROJECTS_DIR, text=True)
            return Success(result)
        except Exception as e:
            return Error(f"Git error: {e}")

    elif tool == "time":
        return Success(time.ctime())

    elif tool == "sqlite":
        db_path = params.get("db_path", os.path.join(PROJECTS_DIR, "test.db"))
        query = params.get("query", "SELECT 1")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(query)
            result = cur.fetchall()
            conn.close()
            return Success(result)
        except Exception as e:
            return Error(f"SQLite error: {e}")

    elif tool == "fetch":
        url = params.get("url")
        if not url:
            return Error("No URL provided")
        try:
            resp = requests.get(url)
            return Success(resp.text)
        except Exception as e:
            return Error(f"Fetch error: {e}")

    elif tool == "sequentialthinking":
        return Success(params)

    elif tool == "postgres":
        query = params.get("query", "SELECT 1")
        conninfo = params.get("conninfo") or os.environ.get("PG_CONNINFO")
        if not conninfo:
            conninfo = (
                f"host={os.environ.get('PGHOST','localhost')} "
                f"port={os.environ.get('PGPORT','5432')} "
                f"dbname={os.environ.get('PGDATABASE','mcp_memory')} "
                f"user={os.environ.get('PGUSER','postgres')} "
                f"password={os.environ.get('PGPASSWORD','postgres')}"
            )
        try:
            conn = psycopg2.connect(conninfo)
            cur = conn.cursor()
            cur.execute(query)
            result = cur.fetchall()
            conn.close()
            return Success(result)
        except Exception as e:
            return Error(f"Postgres error: {e}")

    elif tool == "memory":
        action = params.get("action")
        key = params.get("key")
        value = params.get("value")
        memfile = os.path.join(PROJECTS_DIR, "memory.txt")
        if action == "set" and key and value:
            with open(memfile, "a") as f:
                f.write(f"{key}:{value}\n")
            return Success("OK")
        elif action == "get" and key:
            if not os.path.exists(memfile):
                return Success(None)
            with open(memfile, "r") as f:
                for line in f:
                    k, v = line.strip().split(":", 1)
                    if k == key:
                        return Success(v)
            return Success(None)
        else:
            return Error("Unknown memory action")

    elif tool == "filesystem":
        action = params.get("action")
        if action == "list":
            return Success(os.listdir(PROJECTS_DIR))
        elif action == "read":
            filename = params.get("filename")
            if not filename:
                return Error("No filename provided")
            path = os.path.join(PROJECTS_DIR, filename)
            try:
                with open(path, "r") as f:
                    return Success(f.read())
            except Exception as e:
                return Error(f"Filesystem read error: {e}")
        elif action == "write":
            filename = params.get("filename")
            content = params.get("content", "")
            if not filename:
                return Error("No filename provided")
            path = os.path.join(PROJECTS_DIR, filename)
            try:
                with open(path, "w") as f:
                    f.write(content)
                return Success("OK")
            except Exception as e:
                return Error(f"Filesystem write error: {e}")
        else:
            return Error("Unknown filesystem action")

    elif tool == "web-search":
        # DuckDuckGo HTML scraping (keyless)
        query = params.get("query")
        if not query:
            return Error("No query provided")
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for a in soup.select(".result__a"):
                results.append({"title": a.get_text(), "href": a["href"]})
            return Success(results[:5])
        except Exception as e:
            return Error(f"Web search error: {e}")

    elif tool == "desktop-commander":
        # Stub for desktop-commander - this would typically be handled by the external Smithery server
        return Success({
            "message": "Desktop Commander is available via Smithery",
            "description": "Desktop automation and control via @wonderwhy-er/desktop-commander",
            "available": True
        })

    elif tool == "duckduckgo-mcp-server":
        # Stub for duckduckgo-mcp-server - this would typically be handled by the external Smithery server
        return Success({
            "message": "DuckDuckGo MCP Server is available via Smithery",
            "description": "DuckDuckGo search via @nickclyde/duckduckgo-mcp-server",
            "available": True
        })

    elif tool == "servers":
        # Stub for servers - this would typically be handled by the external Smithery server
        return Success({
            "message": "Servers MCP Server is available via Smithery",
            "description": "Various server tools via @jlia0/servers",
            "available": True
        })

    elif tool == "mcp-server-sqlite-npx":
        # Stub for mcp-server-sqlite-npx - this would typically be handled by the external Smithery server
        return Success({
            "message": "MCP Server SQLite NPX is available via Smithery",
            "description": "SQLite MCP server via mcp-server-sqlite-npx with profile open-tiglon-uqduIK",
            "available": True
        })

    elif tool == "localContextMCP":
        return Success(params)

    return Error(f"Unknown tool: {tool}")

# --- RESOURCES ---

@method
def resources_list():
    try:
        return Success(os.listdir(PROJECTS_DIR))
    except Exception as e:
        return Error(f"Error listing resources: {e}")

@method
def resources_read(resource):
    path = os.path.join(PROJECTS_DIR, resource)
    if not os.path.isfile(path):
        return Error(f"Resource not found: {resource}")
    try:
        with open(path, "r") as f:
            return Success(f.read())
    except Exception as e:
        return Error(f"Error reading resource: {e}")

# --- PROMPTS ---

@method
def prompts_list():
    return Success(["greet", "farewell"])

@method
def prompts_get(prompt):
    prompts = {
        "greet": "Hello, how can I help you?",
        "farewell": "Goodbye!"
    }
    result = prompts.get(prompt, f"Prompt not found: {prompt}")
    return Success(result)

# --- SAMPLING ---

@method
def sampling_createMessage(prompt, context=None):
    return Success(f"Prompt: {prompt}, Context: {context}")

@app.route("/", methods=["POST"])
def index():
    response = dispatch(request.get_data().decode())
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080) 