#!/usr/bin/env python3
"""
Enhanced MCP Server with Cursor-like IDE features
Implements core improvements for distributed development setup
"""

from flask import Flask, request, jsonify
from jsonrpcserver import method, dispatch, Success, Error
import asyncio
import aiohttp
import asyncpg
from typing import Dict, Any, Optional, List
import logging
import os
from pathlib import Path
import json
import hashlib
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enhanced MCP Server with async capabilities
app = Flask(__name__)

# Global connections pool
db_pool = None
desktop_llm_client = None

class DesktopLLMClient:
    """Async client for communicating with desktop LLM"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
        
    async def initialize(self):
        """Initialize async HTTP session"""
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'Content-Type': 'application/json'}
        )
        
    async def call_llm(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make async call to desktop LLM"""
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"LLM returned status {response.status}"}
        except asyncio.TimeoutError:
            logger.error("Desktop LLM request timed out")
            return {"error": "Request timeout"}
        except Exception as e:
            logger.error(f"Desktop LLM error: {e}")
            return {"error": str(e)}
    
    async def stream_completion(self, payload: Dict[str, Any]):
        """Stream completion from desktop LLM"""
        try:
            payload["stream"] = True
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            ) as response:
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode().strip())
                            yield data
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {"error": str(e)}

class CodeContextManager:
    """Manages code context for better RAG"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
    async def get_file_context(self, file_path: str, max_lines: int = 50) -> Dict[str, Any]:
        """Get context around current file"""
        try:
            if not os.path.exists(file_path):
                return {"error": "File not found"}
                
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get file metadata
            file_info = {
                "path": file_path,
                "language": self._detect_language(file_path),
                "line_count": len(lines),
                "size": os.path.getsize(file_path)
            }
            
            # Get recent context (last 50 lines or full file if smaller)
            context_lines = lines[-max_lines:] if len(lines) > max_lines else lines
            
            return {
                "file_info": file_info,
                "context": "".join(context_lines),
                "full_content": len(lines) <= max_lines
            }
            
        except Exception as e:
            logger.error(f"Error getting file context: {e}")
            return {"error": str(e)}
    
    async def get_project_context(self, project_path: str) -> Dict[str, Any]:
        """Get high-level project context"""
        try:
            project_files = []
            for root, dirs, files in os.walk(project_path):
                # Skip common ignore directories
                dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv'}]
                
                for file in files:
                    if self._is_code_file(file):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, project_path)
                        project_files.append({
                            "path": rel_path,
                            "size": os.path.getsize(file_path),
                            "language": self._detect_language(file)
                        })
            
            return {
                "project_path": project_path,
                "file_count": len(project_files),
                "files": project_files[:100],  # Limit to first 100 files
                "languages": list(set(f["language"] for f in project_files))
            }
            
        except Exception as e:
            logger.error(f"Error getting project context: {e}")
            return {"error": str(e)}
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.css': 'css',
            '.html': 'html',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sh': 'bash',
            '.sql': 'sql'
        }
        return language_map.get(ext, 'text')
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file"""
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.css', '.html', '.json', '.xml', '.yaml', '.yml', '.md', '.sh', '.sql',
            '.go', '.rs', '.php', '.rb', '.kt', '.swift', '.scala', '.r', '.m'
        }
        return Path(filename).suffix.lower() in code_extensions

# Enhanced MCP methods with async support
@method
async def enhanced_code_complete(file_path: str, line: int, column: int, context: str, project_path: str):
    """Enhanced code completion with project context"""
    try:
        # Get file and project context
        context_manager = CodeContextManager(db_pool)
        file_context = await context_manager.get_file_context(file_path)
        project_context = await context_manager.get_project_context(project_path)
        
        # Prepare LLM payload with rich context
        llm_payload = {
            "model": "qwen2.5-coder-14B-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": f"""You are an expert code completion assistant. 
                    Project context: {json.dumps(project_context, indent=2)}
                    Current file: {file_context.get('file_info', {})}
                    Provide intelligent code completion suggestions."""
                },
                {
                    "role": "user", 
                    "content": f"""Complete this code at line {line}, column {column}:
                    
                    File: {file_path}
                    Context: {context}
                    Current file content: {file_context.get('context', '')}
                    
                    Provide completions in this format:
                    {{
                        "completions": [
                            {{"text": "completion1", "kind": "function", "detail": "description"}},
                            {{"text": "completion2", "kind": "variable", "detail": "description"}}
                        ]
                    }}"""
                }
            ],
            "temperature": 0.1,
            "max_tokens": 200
        }
        
        # Call desktop LLM
        result = await desktop_llm_client.call_llm(llm_payload)
        
        if "error" in result:
            return Error(f"LLM error: {result['error']}")
            
        # Parse LLM response
        try:
            completion_text = result["choices"][0]["message"]["content"]
            completions = json.loads(completion_text)
            return Success(completions)
        except (KeyError, json.JSONDecodeError) as e:
            return Success({"completions": [{"text": completion_text, "kind": "text", "detail": "Raw completion"}]})
            
    except Exception as e:
        logger.error(f"Code completion error: {e}")
        return Error(str(e))

@method 
async def enhanced_semantic_search(query: str, project_path: str, file_types: List[str] = None):
    """Enhanced semantic search across project"""
    try:
        context_manager = CodeContextManager(db_pool)
        project_context = await context_manager.get_project_context(project_path)
        
        # Filter files by type if specified
        files_to_search = project_context["files"]
        if file_types:
            files_to_search = [f for f in files_to_search if f["language"] in file_types]
        
        search_results = []
        
        # Search through files (simplified - in production, use embeddings)
        for file_info in files_to_search[:20]:  # Limit search
            file_path = os.path.join(project_path, file_info["path"])
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if query.lower() in content:
                        # Get context around match
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if query.lower() in line:
                                start_line = max(0, i - 3)
                                end_line = min(len(lines), i + 4)
                                context = '\n'.join(lines[start_line:end_line])
                                
                                search_results.append({
                                    "file": file_info["path"], 
                                    "line": i + 1,
                                    "context": context,
                                    "language": file_info["language"]
                                })
                                break
            except Exception as e:
                logger.warning(f"Error searching {file_path}: {e}")
                continue
        
        return Success({
            "query": query,
            "results": search_results,
            "total_files_searched": len(files_to_search)
        })
        
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return Error(str(e))

@method
async def project_analyze(project_path: str):
    """Analyze entire project structure and provide insights"""
    try:
        context_manager = CodeContextManager(db_pool)
        project_context = await context_manager.get_project_context(project_path)
        
        # Calculate project statistics
        total_size = sum(f["size"] for f in project_context["files"])
        language_stats = {}
        for file_info in project_context["files"]:
            lang = file_info["language"]
            language_stats[lang] = language_stats.get(lang, 0) + 1
        
        # Identify main language and framework
        main_language = max(language_stats.items(), key=lambda x: x[1])[0] if language_stats else "unknown"
        
        # Look for framework indicators
        framework = "unknown"
        for file_info in project_context["files"]:
            filename = Path(file_info["path"]).name.lower()
            if filename in ["package.json", "requirements.txt", "pom.xml", "cargo.toml"]:
                if filename == "package.json":
                    framework = "node.js"
                elif filename == "requirements.txt":
                    framework = "python"
                elif filename == "pom.xml":
                    framework = "java/maven"
                elif filename == "cargo.toml":
                    framework = "rust"
                break
        
        analysis = {
            "project_path": project_path,
            "total_files": project_context["file_count"],
            "total_size_bytes": total_size,
            "main_language": main_language,
            "framework": framework,
            "language_distribution": language_stats,
            "languages": project_context["languages"]
        }
        
        return Success(analysis)
        
    except Exception as e:
        logger.error(f"Project analysis error: {e}")
        return Error(str(e))

# Initialize async components
async def initialize_async_components():
    """Initialize async database pool and LLM client"""
    global db_pool, desktop_llm_client
    
    # Initialize database pool
    db_config = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "database": os.getenv("PGDATABASE", "mcp_memory"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "postgres"),
    }
    
    try:
        db_pool = await asyncpg.create_pool(**db_config, min_size=5, max_size=20)
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error(f"Database pool initialization failed: {e}")
    
    # Initialize desktop LLM client
    desktop_llm_url = os.getenv("REMOTE_LLM_API_BASE", "http://100.101.230.30:5674")
    desktop_llm_client = DesktopLLMClient(desktop_llm_url)
    await desktop_llm_client.initialize()
    logger.info("Desktop LLM client initialized")

# Keep original sync methods for compatibility
@method
def tools_list():
    """List available tools"""
    return Success([
        "enhanced_code_complete", "enhanced_semantic_search", "project_analyze",
        "git", "time", "sqlite", "fetch", "postgres", "memory", "filesystem", "web-search"
    ])

@method
def tools_call(tool, params=None):
    """Handle tool calls - enhanced version"""
    params = params or {}
    
    if tool == "enhanced_code_complete":
        # Convert to async call
        return asyncio.run(enhanced_code_complete(**params))
    elif tool == "enhanced_semantic_search":
        return asyncio.run(enhanced_semantic_search(**params))
    elif tool == "project_analyze":
        return asyncio.run(project_analyze(**params))
    elif tool == "time":
        return Success(time.ctime())
    else:
        return Error(f"Unknown tool: {tool}")

# Flask routes
@app.route("/", methods=["POST"])
def handle_jsonrpc():
    """Handle JSON-RPC requests"""
    try:
        response = dispatch(request.get_data().decode())
        return jsonify(response)
    except Exception as e:
        logger.error(f"JSON-RPC dispatch error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "database": "connected" if db_pool else "disconnected",
            "desktop_llm": "connected" if desktop_llm_client else "disconnected"
        }
    }
    return jsonify(status)

if __name__ == "__main__":
    # Initialize async components
    asyncio.run(initialize_async_components())
    
    # Start Flask server
    app.run(
        host=os.getenv("MCP_SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_SERVER_PORT", "8080")),
        debug=os.getenv("DEBUG", "false").lower() == "true"
    ) 