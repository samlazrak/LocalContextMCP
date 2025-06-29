#!/usr/bin/env python3
"""
Integrated Enhanced MCP Server with Cursor-like IDE Features
Combines code intelligence, file watching, and extensible language support
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
import time

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

# Enhanced MCP Server with all features
app = Flask(__name__)

# Global instances
db_pool = None
desktop_llm_client = None
project_manager = None

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

# ================== ENHANCED MCP TOOLS ==================

@method
async def project_aware_complete(file_path: str, line: int, column: int, context: str, project_path: str):
    """Project-aware code completion using multiple intelligence sources"""
    try:
        # Get completions from extensible language support
        lang_completions = extensible_code_intelligence.get_completions(file_path, line, column, context)
        
        # Get completions from main code intelligence
        main_completions = code_intelligence.get_completions(file_path, line, column, context)
        
        # Combine and deduplicate
        all_completions = {}
        
        # Add extensible completions
        for comp in lang_completions:
            key = comp.get("text", "")
            if key and key not in all_completions:
                all_completions[key] = comp
        
        # Add main completions
        for comp in main_completions:
            key = comp.get("text", "")
            if key and key not in all_completions:
                all_completions[key] = comp
        
        # Get project context for enhanced completions
        project_analysis = code_intelligence.analyze_project(project_path)
        
        # Prepare enhanced payload for desktop LLM
        llm_payload = {
            "model": "qwen2.5-coder-14B-instruct", 
            "messages": [
                {
                    "role": "system",
                    "content": f"""You are an expert code completion assistant with full project context.
                    
                    Project Analysis:
                    - Total files: {project_analysis.get('total_files', 0)}
                    - Languages: {project_analysis.get('language_distribution', {})}
                    - Total symbols: {project_analysis.get('total_symbols', 0)}
                    
                    Available completions from static analysis: {json.dumps(list(all_completions.values())[:10], indent=2)}
                    
                    Provide intelligent, context-aware completions."""
                },
                {
                    "role": "user",
                    "content": f"""Complete this code at line {line}, column {column}:
                    
                    File: {file_path}
                    Context: {context}
                    
                    Provide completions in JSON format:
                    {{
                        "completions": [
                            {{"text": "completion", "kind": "function", "detail": "description", "score": 0.9}},
                            ...
                        ]
                    }}"""
                }
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }
        
        # Call desktop LLM for enhanced completions
        if desktop_llm_client:
            llm_result = await desktop_llm_client.call_llm(llm_payload)
            
            if "error" not in llm_result:
                try:
                    completion_text = llm_result["choices"][0]["message"]["content"]
                    llm_completions = json.loads(completion_text)
                    
                    # Merge LLM completions with static analysis
                    for comp in llm_completions.get("completions", []):
                        key = comp.get("text", "")
                        if key:
                            all_completions[key] = comp
                except (KeyError, json.JSONDecodeError) as e:
                    logger.warning(f"Could not parse LLM completions: {e}")
        
        # Sort by score if available
        final_completions = sorted(
            all_completions.values(),
            key=lambda x: x.get("score", 0.5),
            reverse=True
        )
        
        return Success({
            "completions": final_completions[:20],  # Limit to top 20
            "context_info": {
                "static_analysis_count": len(lang_completions) + len(main_completions),
                "project_symbols": project_analysis.get('total_symbols', 0),
                "enhanced_by_llm": "error" not in llm_result if desktop_llm_client else False
            }
        })
        
    except Exception as e:
        logger.error(f"Project-aware completion error: {e}")
        return Error(str(e))

@method
async def intelligent_symbol_search(query: str, project_path: str, search_type: str = "all"):
    """Intelligent symbol search across project with multiple backends"""
    try:
        results = []
        
        # Search using main code intelligence
        main_results = code_intelligence.search_symbols(query, project_path)
        results.extend(main_results)
        
        # Search using extensible intelligence
        ext_results = extensible_code_intelligence.search_symbols(query)
        
        # Filter extensible results to project if specified
        if project_path:
            ext_results = [r for r in ext_results if r.get("file_path", "").startswith(project_path)]
        
        results.extend(ext_results)
        
        # Deduplicate based on file + symbol name
        unique_results = {}
        for result in results:
            key = f"{result.get('file', result.get('file_path', ''))}:{result.get('name', '')}"
            if key not in unique_results:
                unique_results[key] = result
        
        # Filter by search type
        if search_type != "all":
            unique_results = {
                k: v for k, v in unique_results.items() 
                if v.get("type", v.get("symbol_type", "")) == search_type
            }
        
        final_results = list(unique_results.values())
        
        # Sort by relevance (exact match first, then prefix, then contains)
        def calculate_relevance(symbol):
            name = symbol.get("name", "").lower()
            query_lower = query.lower()
            
            if name == query_lower:
                return 100
            elif name.startswith(query_lower):
                return 80
            elif query_lower in name:
                return 60
            else:
                return 40
        
        final_results.sort(key=calculate_relevance, reverse=True)
        
        return Success({
            "query": query,
            "results": final_results[:50],  # Limit to top 50
            "total_found": len(final_results),
            "search_backends": ["code_intelligence", "extensible_intelligence"]
        })
        
    except Exception as e:
        logger.error(f"Symbol search error: {e}")
        return Error(str(e))

@method
async def add_project_watch(project_path: str, project_name: str = None):
    """Add a project for real-time monitoring and indexing"""
    try:
        if not project_manager:
            return Error("Project manager not initialized")
        
        result = await project_manager.add_project(project_path, project_name)
        
        if "error" in result:
            return Error(result["error"])
        
        return Success(result)
        
    except Exception as e:
        logger.error(f"Add project watch error: {e}")
        return Error(str(e))

@method
async def remove_project_watch(project_path: str):
    """Remove a project from monitoring"""
    try:
        if not project_manager:
            return Error("Project manager not initialized")
        
        result = await project_manager.remove_project(project_path)
        
        if "error" in result:
            return Error(result["error"])
        
        return Success(result)
        
    except Exception as e:
        logger.error(f"Remove project watch error: {e}")
        return Error(str(e))

@method
async def list_watched_projects():
    """List all projects being monitored"""
    try:
        if not project_manager:
            return Error("Project manager not initialized")
        
        result = await project_manager.list_projects()
        return Success(result)
        
    except Exception as e:
        logger.error(f"List projects error: {e}")
        return Error(str(e))

@method
def get_language_support():
    """Get information about supported languages"""
    try:
        lang_info = extensible_code_intelligence.get_language_info()
        
        # Add code intelligence language info
        main_languages = list(code_intelligence.parsers.keys())
        
        result = {
            "extensible_support": lang_info,
            "main_languages": main_languages,
            "total_supported": len(set(lang_info["supported_languages"] + main_languages))
        }
        
        return Success(result)
        
    except Exception as e:
        logger.error(f"Language support error: {e}")
        return Error(str(e))

@method
def add_language_parser(language_name: str, parser_definition: Dict[str, Any]):
    """Add a new language parser dynamically"""
    try:
        # This would implement dynamic parser creation
        # For now, return information about how to add parsers
        
        return Success({
            "message": f"To add support for {language_name}, create a parser class extending LanguageParserBase",
            "example": {
                "class_name": f"{language_name.title()}Parser",
                "required_methods": ["extract_symbols", "extract_dependencies", "get_file_extensions"],
                "optional_methods": ["validate_syntax", "format_code", "get_completions"]
            },
            "current_support": extensible_code_intelligence.get_language_info()
        })
        
    except Exception as e:
        logger.error(f"Add language parser error: {e}")
        return Error(str(e))

# ================== CORE MCP METHODS ==================

@method
def tools_list():
    """List all available tools"""
    return Success([
        # Enhanced features
        "project_aware_complete", "intelligent_symbol_search", 
        "add_project_watch", "remove_project_watch", "list_watched_projects",
        "get_language_support", "add_language_parser",
        
        # Basic tools
        "git", "time", "sqlite", "fetch", "postgres", "memory", 
        "filesystem", "web-search"
    ])

@method
def tools_call(tool, params=None):
    """Handle tool calls with enhanced routing"""
    params = params or {}
    
    # Enhanced tools (async)
    if tool == "project_aware_complete":
        return asyncio.run(project_aware_complete(**params))
    elif tool == "intelligent_symbol_search":
        return asyncio.run(intelligent_symbol_search(**params))
    elif tool == "add_project_watch":
        return asyncio.run(add_project_watch(**params))
    elif tool == "remove_project_watch":
        return asyncio.run(remove_project_watch(**params))
    elif tool == "list_watched_projects":
        return asyncio.run(list_watched_projects())
    
    # Enhanced tools (sync)
    elif tool == "get_language_support":
        return get_language_support()
    elif tool == "add_language_parser":
        return add_language_parser(**params)
    
    # Basic tools
    elif tool == "time":
        return Success(time.ctime())
    else:
        return Error(f"Unknown tool: {tool}")

# ================== INITIALIZATION ==================

async def initialize_enhanced_components():
    """Initialize all enhanced components"""
    global db_pool, desktop_llm_client, project_manager
    
    logger.info("Initializing enhanced MCP server components...")
    
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
        logger.info("✅ Database pool initialized")
    except Exception as e:
        logger.error(f"❌ Database pool initialization failed: {e}")
    
    # Initialize desktop LLM client
    desktop_llm_url = os.getenv("REMOTE_LLM_API_BASE", "http://100.101.230.30:5674")
    desktop_llm_client = DesktopLLMClient(desktop_llm_url)
    await desktop_llm_client.initialize()
    logger.info("✅ Desktop LLM client initialized")
    
    # Initialize project manager with file watching
    project_manager = ProjectManager(code_intelligence, db_pool)
    logger.info("✅ Project manager initialized")
    
    logger.info("🚀 Enhanced MCP server fully initialized!")

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

@app.route("/health", methods=["GET"])
def health_check():
    """Enhanced health check with component status"""
    status = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "database": "connected" if db_pool else "disconnected",
            "desktop_llm": "connected" if desktop_llm_client else "disconnected", 
            "project_manager": "active" if project_manager else "inactive",
            "code_intelligence": "loaded",
            "extensible_intelligence": "loaded"
        },
        "features": {
            "project_aware_completions": True,
            "real_time_file_watching": True,
            "extensible_language_support": True,
            "semantic_search": True
        }
    }
    
    # Add project manager status if available
    if project_manager:
        try:
            watch_status = project_manager.indexer.get_watch_status()
            status["project_manager_details"] = watch_status
        except:
            pass
    
    return jsonify(status)

@app.route("/api/languages", methods=["GET"]) 
def api_languages():
    """REST API endpoint for language support info"""
    try:
        result = get_language_support()
        if isinstance(result, Success):
            return jsonify(result.result)
        else:
            return jsonify({"error": result.message}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Initialize enhanced components
    asyncio.run(initialize_enhanced_components())
    
    # Start Flask server
    app.run(
        host=os.getenv("MCP_SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_SERVER_PORT", "8080")),
        debug=os.getenv("DEBUG", "false").lower() == "true"
    ) 