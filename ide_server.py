#!/usr/bin/env python3
"""
Local IDE Server - A functional alternative to Cursor IDE
Provides comprehensive IDE features including LSP integration, AI assistance, and file management
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from jsonrpcserver import method, dispatch, Success, Error
import asyncio
import aiohttp
import asyncpg
import logging
import os
import json
import time
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid
import tempfile
import shutil

# Import our enhanced modules
from code_intelligence import code_intelligence
from file_watcher import ProjectManager
from language_support import extensible_code_intelligence

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app with SocketIO for real-time communication
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global instances
db_pool = None
project_manager = None
active_sessions = {}  # session_id -> session_info
lsp_servers = {}  # language -> LSP server process

class IDESession:
    """Represents an IDE session with workspace and settings"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.workspace_path = None
        self.open_files = {}  # file_path -> file_content
        self.recent_files = []
        self.settings = {
            "theme": "dark",
            "font_size": 14,
            "tab_size": 4,
            "auto_save": True,
            "ai_assistance": True
        }
        self.created_at = time.time()

class LanguageServerManager:
    """Manages Language Server Protocol (LSP) servers"""
    
    def __init__(self):
        self.servers = {}
        self.server_configs = {
            'python': {
                'command': ['pylsp'],
                'init_options': {}
            },
            'javascript': {
                'command': ['typescript-language-server', '--stdio'],
                'init_options': {}
            },
            'typescript': {
                'command': ['typescript-language-server', '--stdio'],
                'init_options': {}
            }
        }
    
    async def start_server(self, language: str, workspace_path: str):
        """Start LSP server for a language"""
        if language not in self.server_configs:
            return None
        
        config = self.server_configs[language]
        try:
            process = await asyncio.create_subprocess_exec(
                *config['command'],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.servers[language] = {
                'process': process,
                'workspace': workspace_path,
                'initialized': False
            }
            
            # Initialize the LSP server
            await self._initialize_server(language, workspace_path)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start LSP server for {language}: {e}")
            return None
    
    async def _initialize_server(self, language: str, workspace_path: str):
        """Initialize LSP server with workspace"""
        server = self.servers[language]
        process = server['process']
        
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": f"file://{workspace_path}",
                "capabilities": {
                    "textDocument": {
                        "completion": {"completionItem": {"snippetSupport": True}},
                        "hover": {},
                        "signatureHelp": {},
                        "definition": {},
                        "references": {},
                        "documentSymbol": {},
                        "workspaceSymbol": {},
                        "codeAction": {},
                        "formatting": {}
                    }
                }
            }
        }
        
        try:
            message = json.dumps(init_request) + '\n'
            process.stdin.write(f"Content-Length: {len(message)}\r\n\r\n{message}".encode())
            await process.stdin.drain()
            server['initialized'] = True
            logger.info(f"LSP server for {language} initialized")
        except Exception as e:
            logger.error(f"Failed to initialize LSP server for {language}: {e}")

# Initialize global instances
lsp_manager = LanguageServerManager()

# ================== IDE API ENDPOINTS ==================

@method
async def create_session():
    """Create a new IDE session"""
    session_id = str(uuid.uuid4())
    session = IDESession(session_id)
    active_sessions[session_id] = session
    
    return Success({
        "session_id": session_id,
        "created_at": session.created_at
    })

@method
async def open_workspace(session_id: str, workspace_path: str):
    """Open a workspace in the IDE"""
    try:
        if session_id not in active_sessions:
            return Error("Invalid session ID")
        
        session = active_sessions[session_id]
        
        if not os.path.exists(workspace_path):
            return Error("Workspace path does not exist")
        
        session.workspace_path = workspace_path
        
        # Start project monitoring
        if project_manager:
            await project_manager.add_project(workspace_path, Path(workspace_path).name)
        
        # Analyze project structure
        project_analysis = code_intelligence.analyze_project(workspace_path)
        
        # Start LSP servers for detected languages
        languages = project_analysis.get('language_distribution', {})
        for language in languages.keys():
            await lsp_manager.start_server(language, workspace_path)
        
        return Success({
            "workspace_path": workspace_path,
            "project_analysis": project_analysis,
            "lsp_servers_started": list(languages.keys())
        })
        
    except Exception as e:
        logger.error(f"Error opening workspace: {e}")
        return Error(str(e))

@method
async def get_file_tree(session_id: str, path: Optional[str] = None):
    """Get file tree for workspace or specific path"""
    try:
        if session_id not in active_sessions:
            return Error("Invalid session ID")
        
        session = active_sessions[session_id]
        base_path = path or session.workspace_path
        
        if not base_path or not os.path.exists(base_path):
            return Error("Invalid path")
        
        def build_tree(directory):
            tree = []
            try:
                for item in sorted(os.listdir(directory)):
                    if item.startswith('.'):
                        continue
                    
                    item_path = os.path.join(directory, item)
                    relative_path = os.path.relpath(item_path, session.workspace_path)
                    
                    if os.path.isdir(item_path):
                        tree.append({
                            "name": item,
                            "type": "directory",
                            "path": relative_path,
                            "children": build_tree(item_path) if len(os.listdir(item_path)) < 100 else []
                        })
                    else:
                        tree.append({
                            "name": item,
                            "type": "file",
                            "path": relative_path,
                            "size": os.path.getsize(item_path),
                            "language": _detect_language(item)
                        })
            except PermissionError:
                pass
            return tree
        
        file_tree = build_tree(base_path)
        
        return Success({
            "path": base_path,
            "tree": file_tree
        })
        
    except Exception as e:
        logger.error(f"Error getting file tree: {e}")
        return Error(str(e))

@method
async def open_file(session_id: str, file_path: str):
    """Open a file in the IDE"""
    try:
        if session_id not in active_sessions:
            return Error("Invalid session ID")
        
        session = active_sessions[session_id]
        
        # Make path absolute if it's relative to workspace
        if session.workspace_path and not os.path.isabs(file_path):
            full_path = os.path.join(session.workspace_path, file_path)
        else:
            full_path = file_path
        
        if not os.path.exists(full_path):
            return Error("File does not exist")
        
        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding or treat as binary
            with open(full_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Store in session
        session.open_files[file_path] = content
        
        # Add to recent files
        if file_path not in session.recent_files:
            session.recent_files.insert(0, file_path)
            session.recent_files = session.recent_files[:20]  # Keep last 20
        
        # Get file analysis
        analysis = code_intelligence.analyze_file(full_path)
        
        return Success({
            "file_path": file_path,
            "content": content,
            "language": _detect_language(file_path),
            "size": len(content),
            "analysis": analysis,
            "encoding": "utf-8"
        })
        
    except Exception as e:
        logger.error(f"Error opening file: {e}")
        return Error(str(e))

@method
async def save_file(session_id: str, file_path: str, content: str):
    """Save file content"""
    try:
        if session_id not in active_sessions:
            return Error("Invalid session ID")
        
        session = active_sessions[session_id]
        
        # Make path absolute if it's relative to workspace
        if session.workspace_path and not os.path.isabs(file_path):
            full_path = os.path.join(session.workspace_path, file_path)
        else:
            full_path = file_path
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Save file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update session
        session.open_files[file_path] = content
        
        # Re-analyze file
        analysis = code_intelligence.analyze_file(full_path)
        
        return Success({
            "file_path": file_path,
            "saved": True,
            "size": len(content),
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return Error(str(e))

@method
async def get_completions(session_id: str, file_path: str, line: int, column: int, content: str):
    """Get code completions at cursor position"""
    try:
        if session_id not in active_sessions:
            return Error("Invalid session ID")
        
        session = active_sessions[session_id]
        
        # Get completions from multiple sources
        completions = []
        
        # Static analysis completions
        if session.workspace_path:
            full_path = os.path.join(session.workspace_path, file_path) if not os.path.isabs(file_path) else file_path
            static_completions = code_intelligence.get_completions(full_path, line, column, content)
            completions.extend(static_completions)
        
        # Extensible language support completions
        ext_completions = extensible_code_intelligence.get_completions(file_path, line, column, content)
        completions.extend(ext_completions)
        
        # AI-powered completions (if enabled)
        if session.settings.get("ai_assistance", True):
            ai_completions = await _get_ai_completions(file_path, line, column, content, session.workspace_path)
            completions.extend(ai_completions)
        
        # Deduplicate and rank
        unique_completions = {}
        for comp in completions:
            text = comp.get("text", "")
            if text and text not in unique_completions:
                unique_completions[text] = comp
        
        ranked_completions = sorted(
            unique_completions.values(),
            key=lambda x: x.get("score", 0.5),
            reverse=True
        )
        
        return Success({
            "completions": ranked_completions[:50],
            "line": line,
            "column": column
        })
        
    except Exception as e:
        logger.error(f"Error getting completions: {e}")
        return Error(str(e))

@method
async def execute_command(session_id: str, command: str, cwd: Optional[str] = None):
    """Execute a command in the workspace"""
    try:
        if session_id not in active_sessions:
            return Error("Invalid session ID")
        
        session = active_sessions[session_id]
        working_dir = cwd or session.workspace_path
        
        if not working_dir:
            return Error("No workspace set")
        
        # Security: Only allow certain commands or whitelist patterns
        allowed_commands = [
            'ls', 'dir', 'pwd', 'git', 'npm', 'pip', 'python', 'node', 'tsc',
            'pytest', 'jest', 'cargo', 'go', 'javac', 'mvn', 'gradle'
        ]
        
        cmd_parts = command.split()
        if not cmd_parts or cmd_parts[0] not in allowed_commands:
            return Error("Command not allowed")
        
        # Execute command
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return Success({
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "cwd": working_dir
            })
            
        except subprocess.TimeoutExpired:
            return Error("Command timed out")
        except Exception as e:
            return Error(f"Command execution failed: {e}")
        
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return Error(str(e))

@method
async def search_workspace(session_id: str, query: str, file_types: Optional[List[str]] = None, max_results: int = 100):
    """Search for text across workspace files"""
    try:
        if session_id not in active_sessions:
            return Error("Invalid session ID")
        
        session = active_sessions[session_id]
        
        if not session.workspace_path:
            return Error("No workspace set")
        
        results = []
        search_count = 0
        
        for root, dirs, files in os.walk(session.workspace_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if search_count >= max_results:
                    break
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, session.workspace_path)
                
                # Filter by file types if specified
                if file_types:
                    file_ext = Path(file).suffix.lower()
                    if file_ext not in file_types:
                        continue
                
                # Skip binary files
                if not _is_text_file(file_path):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Search for query in content
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if query.lower() in line.lower():
                            results.append({
                                "file": relative_path,
                                "line": line_num,
                                "content": line.strip(),
                                "match_start": line.lower().find(query.lower()),
                                "match_end": line.lower().find(query.lower()) + len(query)
                            })
                            search_count += 1
                            
                            if search_count >= max_results:
                                break
                
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        return Success({
            "query": query,
            "results": results,
            "total_matches": len(results)
        })
        
    except Exception as e:
        logger.error(f"Error searching workspace: {e}")
        return Error(str(e))

@method
async def get_git_status(session_id: str):
    """Get git status for the workspace"""
    try:
        if session_id not in active_sessions:
            return Error("Invalid session ID")
        
        session = active_sessions[session_id]
        
        if not session.workspace_path:
            return Error("No workspace set")
        
        try:
            # Get git status
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=session.workspace_path,
                capture_output=True,
                text=True
            )
            
            # Get current branch
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=session.workspace_path,
                capture_output=True,
                text=True
            )
            
            # Parse status output
            files = []
            for line in status_result.stdout.strip().split('\n'):
                if line:
                    status_code = line[:2]
                    file_path = line[3:]
                    files.append({
                        "path": file_path,
                        "status": status_code.strip(),
                        "staged": status_code[0] != ' ',
                        "modified": status_code[1] != ' '
                    })
            
            return Success({
                "branch": branch_result.stdout.strip(),
                "files": files,
                "is_repo": status_result.returncode == 0
            })
            
        except FileNotFoundError:
            return Error("Git not found")
        except Exception as e:
            return Error(f"Git operation failed: {e}")
        
    except Exception as e:
        logger.error(f"Error getting git status: {e}")
        return Error(str(e))

# ================== HELPER FUNCTIONS ==================

async def _get_ai_completions(file_path: str, line: int, column: int, content: str, workspace_path: str) -> List[Dict]:
    """Get AI-powered completions using LLM"""
    try:
        # This would integrate with your LLM service
        # For now, return empty list
        return []
    except Exception as e:
        logger.error(f"AI completion error: {e}")
        return []

def _detect_language(file_path: str) -> str:
    """Detect programming language from file extension"""
    ext = Path(file_path).suffix.lower()
    language_map = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'javascript', '.tsx': 'typescript', '.java': 'java',
        '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.hpp': 'cpp',
        '.css': 'css', '.html': 'html', '.json': 'json',
        '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
        '.md': 'markdown', '.sh': 'bash', '.sql': 'sql',
        '.go': 'go', '.rs': 'rust', '.php': 'php', '.rb': 'ruby'
    }
    return language_map.get(ext, 'text')

def _is_text_file(file_path: str) -> bool:
    """Check if file is a text file"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
        return b'\x00' not in chunk
    except:
        return False

# ================== WEBSOCKET EVENTS ==================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to IDE server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('file_change')
def handle_file_change(data):
    """Handle real-time file changes"""
    file_path = data.get('file_path')
    content = data.get('content')
    session_id = data.get('session_id')
    
    if session_id in active_sessions:
        session = active_sessions[session_id]
        session.open_files[file_path] = content
        
        # Broadcast change to other clients in same session
        emit('file_updated', {
            'file_path': file_path,
            'content': content
        }, broadcast=True, include_self=False)

# ================== CORE MCP METHODS ==================

@method
def tools_list():
    """List all available IDE tools"""
    return Success([
        # IDE-specific tools
        "create_session", "open_workspace", "get_file_tree", "open_file", "save_file",
        "get_completions", "execute_command", "search_workspace", "get_git_status",
        
        # Enhanced features from existing modules
        "project_aware_complete", "intelligent_symbol_search", 
        "add_project_watch", "remove_project_watch", "list_watched_projects",
        "get_language_support",
        
        # Basic tools
        "git", "time", "filesystem", "web-search"
    ])

@method
def tools_call(tool, params=None):
    """Handle tool calls"""
    params = params or {}
    
    # IDE tools (async)
    if tool == "create_session":
        return asyncio.run(create_session())
    elif tool == "open_workspace":
        return asyncio.run(open_workspace(**params))
    elif tool == "get_file_tree":
        return asyncio.run(get_file_tree(**params))
    elif tool == "open_file":
        return asyncio.run(open_file(**params))
    elif tool == "save_file":
        return asyncio.run(save_file(**params))
    elif tool == "get_completions":
        return asyncio.run(get_completions(**params))
    elif tool == "execute_command":
        return asyncio.run(execute_command(**params))
    elif tool == "search_workspace":
        return asyncio.run(search_workspace(**params))
    elif tool == "get_git_status":
        return asyncio.run(get_git_status(**params))
    elif tool == "time":
        return Success(time.ctime())
    else:
        return Error(f"Unknown tool: {tool}")

# ================== FLASK ROUTES ==================

@app.route("/", methods=["POST"])
def handle_jsonrpc():
    """Handle JSON-RPC requests"""
    try:
        response = dispatch(request.get_data().decode())
        return jsonify(response)
    except Exception as e:
        logger.error(f"JSON-RPC dispatch error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def serve_ide():
    """Serve the IDE web interface"""
    return send_from_directory('static', 'index.html')

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "active_sessions": len(active_sessions),
        "lsp_servers": list(lsp_servers.keys()),
        "features": {
            "file_management": True,
            "code_completion": True,
            "git_integration": True,
            "workspace_search": True,
            "real_time_collaboration": True
        }
    })

# ================== INITIALIZATION ==================

async def initialize_ide_server():
    """Initialize IDE server components"""
    global project_manager, db_pool
    
    logger.info("Initializing IDE server...")
    
    # Initialize database pool (optional)
    try:
        db_config = {
            "host": os.getenv("PGHOST", "localhost"),
            "port": int(os.getenv("PGPORT", "5432")),
            "database": os.getenv("PGDATABASE", "mcp_memory"),
            "user": os.getenv("PGUSER", "postgres"),
            "password": os.getenv("PGPASSWORD", "postgres"),
        }
        db_pool = await asyncpg.create_pool(**db_config, min_size=2, max_size=10)
        logger.info("✅ Database pool initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database pool initialization failed: {e}")
    
    # Initialize project manager
    project_manager = ProjectManager(code_intelligence, db_pool)
    logger.info("✅ Project manager initialized")
    
    logger.info("🚀 IDE server fully initialized!")

if __name__ == "__main__":
    # Initialize components
    asyncio.run(initialize_ide_server())
    
    # Start the server
    socketio.run(
        app,
        host=os.getenv("IDE_SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("IDE_SERVER_PORT", "3000")),
        debug=os.getenv("DEBUG", "false").lower() == "true"
    )