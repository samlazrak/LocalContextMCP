#!/usr/bin/env python3
"""
Comprehensive MCP Meta-Server for Void IDE Integration
Aggregates all useful local MCP servers into one powerful system
"""

import asyncio
import aiohttp
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import importlib.util
import sys

from flask import Flask, request, jsonify
from jsonrpcserver import method, dispatch, Success, Error
import asyncpg
from concurrent.futures import ThreadPoolExecutor

# Import enhanced modules
from code_intelligence import CodeIntelligence
from file_watcher import ProjectManager
from language_support import extensible_code_intelligence

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_mcp.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """Configuration for individual MCP servers"""
    name: str
    type: str  # local, remote, builtin
    command: Optional[str] = None
    args: Optional[List[str]] = None
    port: Optional[int] = None
    url: Optional[str] = None
    enabled: bool = True
    health_check_url: Optional[str] = None
    description: str = ""
    tools: Optional[List[str]] = None

@dataclass  
class LLMConfig:
    """Configuration for LLM endpoints"""
    name: str
    endpoint: str
    api_key: Optional[str] = None
    model: str = ""
    type: str = "local"  # local, remote
    max_tokens: int = 4096
    temperature: float = 0.1

class ComprehensiveMCPServer:
    """Meta-MCP server that aggregates all useful MCP servers"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.db_pool = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # LLM clients
        self.deepseek_client = None
        self.granite_client = None
        
        # Core components
        self.code_intelligence = CodeIntelligence()
        self.project_manager = None
        
        # MCP server registry
        self.mcp_servers = {}
        self.server_processes = {}
        
        # Load configuration
        self.load_configurations()
        
    def load_configurations(self):
        """Load MCP server and LLM configurations"""
        
        # LLM Configurations
        self.llm_configs = {
            "deepseek": LLMConfig(
                name="DeepSeek-Coder-v2-lite-instruct",
                endpoint=os.getenv("DEEPSEEK_API_BASE", "http://localhost:8000/v1"),
                api_key=None,  # No API key needed for local/direct connection
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-coder"),
                type="local",  # Changed from remote to local
                max_tokens=8192,
                temperature=0.1
            ),
            "granite": LLMConfig(
                name="Granite-3.1-8B",
                endpoint=os.getenv("GRANITE_API_BASE", "http://localhost:11434/v1"),
                model="granite3.1:8b",
                type="local",
                max_tokens=4096,
                temperature=0.1
            )
        }
        
        # Comprehensive MCP Server Registry
        self.mcp_server_configs = {
            # Essential Development Tools
            "filesystem": MCPServerConfig(
                name="Filesystem", type="builtin",
                description="Secure file operations with configurable access",
                tools=["read_file", "write_file", "create_directory", "list_directory", "delete_file"]
            ),
            "git": MCPServerConfig(
                name="Git", type="builtin", 
                description="Git repository management and operations",
                tools=["git_status", "git_commit", "git_push", "git_pull", "git_branch", "git_diff"]
            ),
            "github": MCPServerConfig(
                name="GitHub", type="remote",
                command="npx", args=["@modelcontextprotocol/server-github"],
                description="GitHub repository integration and management",
                tools=["create_issue", "create_pr", "search_repos", "get_file_contents"]
            ),
            
            # Database Tools
            "postgres": MCPServerConfig(
                name="PostgreSQL", type="builtin",
                description="PostgreSQL database operations",
                tools=["query", "schema_info", "table_info"]
            ),
            "sqlite": MCPServerConfig(
                name="SQLite", type="remote",
                command="npx", args=["@modelcontextprotocol/server-sqlite"],
                description="SQLite database operations",
                tools=["query", "schema", "tables"]
            ),
            "mysql": MCPServerConfig(
                name="MySQL", type="remote", 
                command="docker", args=["run", "-i", "--rm", "mysql-mcp"],
                description="MySQL database integration",
                tools=["query", "schema_inspection", "data_operations"]
            ),
            
            # Web and Search Tools
            "web-search": MCPServerConfig(
                name="Web Search", type="remote",
                command="npx", args=["@modelcontextprotocol/server-brave-search"],
                description="Web search capabilities",
                tools=["search", "get_page_content"]
            ),
            "fetch": MCPServerConfig(
                name="Fetch", type="remote",
                command="npx", args=["@modelcontextprotocol/server-fetch"],
                description="Web content fetching and conversion",
                tools=["fetch_url", "fetch_html", "fetch_json"]
            ),
            "puppeteer": MCPServerConfig(
                name="Puppeteer", type="remote",
                command="npx", args=["@modelcontextprotocol/server-puppeteer"],
                description="Browser automation and web scraping",
                tools=["screenshot", "scrape", "navigate", "fill_form"]
            ),
            
            # Development and DevOps
            "docker": MCPServerConfig(
                name="Docker", type="remote",
                command="npx", args=["mcp-docker-server"],
                description="Docker container management",
                tools=["list_containers", "run_container", "stop_container", "build_image"]
            ),
            "kubernetes": MCPServerConfig(
                name="Kubernetes", type="remote",
                command="npx", args=["k8s-mcp-server"],
                description="Kubernetes cluster management",
                tools=["get_pods", "get_services", "apply_manifest", "get_logs"]
            ),
            
            # Code Analysis and Quality
            "eslint": MCPServerConfig(
                name="ESLint", type="builtin",
                description="JavaScript/TypeScript linting",
                tools=["lint_file", "fix_lint_issues", "get_lint_config"]
            ),
            "black": MCPServerConfig(
                name="Black", type="builtin",
                description="Python code formatting",
                tools=["format_code", "check_format"]
            ),
            "prettier": MCPServerConfig(
                name="Prettier", type="builtin", 
                description="Code formatting for multiple languages",
                tools=["format_code", "check_format"]
            ),
            
            # Testing Tools  
            "pytest": MCPServerConfig(
                name="PyTest", type="builtin",
                description="Python testing framework",
                tools=["run_tests", "discover_tests", "generate_test"]
            ),
            "jest": MCPServerConfig(
                name="Jest", type="builtin",
                description="JavaScript testing framework", 
                tools=["run_tests", "run_coverage", "watch_tests"]
            ),
            
            # Memory and Context
            "memory": MCPServerConfig(
                name="Memory", type="remote",
                command="npx", args=["@modelcontextprotocol/server-memory"],
                description="Persistent memory and context management",
                tools=["store_memory", "retrieve_memory", "search_memory"]
            ),
            "sequential-thinking": MCPServerConfig(
                name="Sequential Thinking", type="remote",
                command="npx", args=["@modelcontextprotocol/server-sequential-thinking"],
                description="Dynamic problem-solving through thought sequences",
                tools=["think", "reason", "plan"]
            ),
            
            # Time and Scheduling
            "time": MCPServerConfig(
                name="Time", type="remote",
                command="npx", args=["@modelcontextprotocol/server-time"],
                description="Time and timezone operations",
                tools=["current_time", "convert_timezone", "format_time"]
            ),
            
            # Communication Tools
            "slack": MCPServerConfig(
                name="Slack", type="remote",
                command="npx", args=["@modelcontextprotocol/server-slack"],
                description="Slack integration and messaging",
                tools=["send_message", "get_channels", "get_messages"]
            ),
            "discord": MCPServerConfig(
                name="Discord", type="remote",
                command="npx", args=["discord-mcp-server"],
                description="Discord bot integration",
                tools=["send_message", "get_channels", "manage_server"]
            ),
            
            # Cloud Services
            "aws": MCPServerConfig(
                name="AWS", type="remote",
                command="npx", args=["aws-mcp-server"],
                description="AWS cloud services integration",
                tools=["s3_operations", "ec2_management", "lambda_functions"]
            ),
            "azure": MCPServerConfig(
                name="Azure", type="remote", 
                command="npx", args=["azure-mcp-server"],
                description="Microsoft Azure integration",
                tools=["resource_management", "storage_operations", "vm_management"]
            ),
            
            # AI and ML Tools
            "huggingface": MCPServerConfig(
                name="HuggingFace", type="remote",
                command="npx", args=["huggingface-mcp-server"],
                description="HuggingFace model integration",
                tools=["search_models", "load_model", "run_inference"]
            ),
            "openai": MCPServerConfig(
                name="OpenAI", type="remote",
                command="npx", args=["openai-mcp-server"],
                description="OpenAI API integration",
                tools=["chat_completion", "text_embedding", "image_generation"]
            ),
            
            # Productivity Tools
            "notion": MCPServerConfig(
                name="Notion", type="remote",
                command="npx", args=["@modelcontextprotocol/server-notion"],
                description="Notion workspace integration",
                tools=["create_page", "search_pages", "update_page"]
            ),
            "google-drive": MCPServerConfig(
                name="Google Drive", type="remote",
                command="npx", args=["google-drive-mcp-server"],
                description="Google Drive file management",
                tools=["list_files", "upload_file", "download_file", "share_file"]
            ),
            
            # Security and Monitoring
            "sentry": MCPServerConfig(
                name="Sentry", type="remote",
                command="npx", args=["@modelcontextprotocol/server-sentry"],
                description="Error tracking and monitoring",
                tools=["get_issues", "create_issue", "resolve_issue"]
            ),
        }

    async def initialize_llm_clients(self):
        """Initialize LLM clients for DeepSeek and Granite"""
        logger.info("Initializing LLM clients...")
        
        # DeepSeek client (now local/direct connection)
        self.deepseek_client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        )
        logger.info("✅ DeepSeek client initialized (direct connection)")
        
        # Granite client (local)
        self.granite_client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        logger.info("✅ LLM clients initialized")

    async def start_mcp_servers(self):
        """Start all configured MCP servers"""
        logger.info("Starting MCP servers...")
        
        for server_name, config in self.mcp_server_configs.items():
            if not config.enabled:
                continue
                
            try:
                if config.type == "remote" and config.command:
                    # Start remote MCP server as subprocess
                    process = subprocess.Popen(
                        [config.command] + (config.args or []),
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    self.server_processes[server_name] = process
                    logger.info(f"✅ Started MCP server: {server_name}")
                    
                elif config.type == "builtin":
                    # Built-in servers are handled directly
                    logger.info(f"✅ Built-in MCP server ready: {server_name}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to start MCP server {server_name}: {e}")

    async def initialize_database(self):
        """Initialize PostgreSQL connection pool"""
        db_config = {
            "host": os.getenv("PGHOST", "localhost"),
            "port": int(os.getenv("PGPORT", "5432")),
            "database": os.getenv("PGDATABASE", "comprehensive_mcp"),
            "user": os.getenv("PGUSER", "postgres"),
            "password": os.getenv("PGPASSWORD", "postgres"),
        }
        
        try:
            self.db_pool = await asyncpg.create_pool(**db_config, min_size=5, max_size=20)
            logger.info("✅ Database pool initialized")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")

    async def call_llm(self, prompt: str, model: str = "granite", **kwargs) -> Dict[str, Any]:
        """Call appropriate LLM based on task complexity"""
        
        # Route to appropriate model
        if model == "deepseek" or "complex" in kwargs.get("task_type", ""):
            client = self.deepseek_client
            config = self.llm_configs["deepseek"]
        else:
            client = self.granite_client  
            config = self.llm_configs["granite"]
        
        if client is None:
            return {"error": f"LLM client not initialized for model: {model}"}
        
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", config.max_tokens),
            "temperature": kwargs.get("temperature", config.temperature)
        }
        
        try:
            async with client.post(f"{config.endpoint}/chat/completions", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"LLM API returned status {response.status}"}
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"error": str(e)}

    # ================== MCP METHODS ==================

    @method
    async def tools_list(self):
        """List all available tools from all MCP servers"""
        all_tools = []
        
        # Add tools from all enabled servers
        for server_name, config in self.mcp_server_configs.items():
            if config.enabled and config.tools:
                for tool in config.tools:
                    all_tools.append(f"{server_name}_{tool}")
        
        # Add built-in comprehensive tools
        comprehensive_tools = [
            "comprehensive_code_completion",
            "project_analysis", 
            "intelligent_search",
            "multi_language_support",
            "context_aware_suggestions",
            "ai_assisted_debugging",
            "automated_testing",
            "code_generation",
            "documentation_generation",
            "refactoring_suggestions"
        ]
        
        all_tools.extend(comprehensive_tools)
        return Success(all_tools)

    @method
    async def comprehensive_code_completion(
        self, 
        file_path: str, 
        line: int, 
        column: int, 
        context: str,
        project_path: str,
        language: str = None
    ):
        """Comprehensive code completion using multiple intelligence sources"""
        try:
            # Get project analysis
            project_analysis = self.code_intelligence.analyze_project(project_path)
            
            # Get multiple completion sources
            main_completions = self.code_intelligence.get_completions(file_path, line, column, context)
            ext_completions = extensible_code_intelligence.get_completions(file_path, line, column, context)
            
            # Prepare enhanced prompt for LLM
            llm_prompt = f"""
            You are an expert code completion assistant with full project context.
            
            Project Analysis:
            - Total files: {project_analysis.get('total_files', 0)}
            - Languages: {project_analysis.get('language_distribution', {})}
            - Total symbols: {project_analysis.get('total_symbols', 0)}
            
            File: {file_path}
            Language: {language or 'auto-detect'}
            Position: Line {line}, Column {column}
            Context: {context}
            
            Available static completions: {json.dumps(main_completions[:5], indent=2)}
            
            Provide intelligent, context-aware code completions in JSON format:
            {{
                "completions": [
                    {{"text": "completion", "kind": "function", "detail": "description", "score": 0.9}},
                    ...
                ]
            }}
            """
            
            # Determine model based on complexity
            model = "deepseek" if len(context) > 1000 or project_analysis.get('total_symbols', 0) > 100 else "granite"
            
            llm_result = await self.call_llm(llm_prompt, model=model, task_type="code_completion")
            
            # Combine all completions
            all_completions = main_completions + ext_completions
            
            if "error" not in llm_result:
                try:
                    completion_text = llm_result["choices"][0]["message"]["content"]
                    llm_completions = json.loads(completion_text)
                    all_completions.extend(llm_completions.get("completions", []))
                except (KeyError, json.JSONDecodeError) as e:
                    logger.warning(f"Could not parse LLM completions: {e}")
            
            # Remove duplicates and sort by score
            unique_completions = {}
            for comp in all_completions:
                key = comp.get("text", "")
                if key and key not in unique_completions:
                    unique_completions[key] = comp
            
            final_completions = sorted(
                unique_completions.values(),
                key=lambda x: x.get("score", 0.5),
                reverse=True
            )
            
            return Success({
                "completions": final_completions[:25],
                "context_info": {
                    "static_analysis_count": len(main_completions) + len(ext_completions),
                    "project_symbols": project_analysis.get('total_symbols', 0),
                    "ai_enhanced": "error" not in llm_result,
                    "model_used": model
                }
            })
            
        except Exception as e:
            logger.error(f"Comprehensive code completion error: {e}")
            return Error(str(e))

    @method
    async def project_analysis(self, project_path: str, deep_analysis: bool = False):
        """Comprehensive project analysis with AI insights"""
        try:
            # Get basic project analysis
            basic_analysis = self.code_intelligence.analyze_project(project_path)
            
            if deep_analysis:
                # Use DeepSeek for complex analysis
                analysis_prompt = f"""
                Analyze this software project comprehensively:
                
                Project Path: {project_path}
                Total Files: {basic_analysis.get('total_files', 0)}
                Languages: {basic_analysis.get('language_distribution', {})}
                Total Symbols: {basic_analysis.get('total_symbols', 0)}
                
                Symbols by Type: {basic_analysis.get('symbol_distribution', {})}
                
                Provide insights on:
                1. Architecture patterns used
                2. Code quality assessment
                3. Potential improvements
                4. Security considerations
                5. Performance optimization opportunities
                6. Testing coverage recommendations
                7. Documentation needs
                
                Return analysis in JSON format.
                """
                
                ai_analysis = await self.call_llm(
                    analysis_prompt, 
                    model="deepseek", 
                    task_type="complex",
                    max_tokens=4096
                )
                
                if "error" not in ai_analysis:
                    try:
                        ai_insights = json.loads(ai_analysis["choices"][0]["message"]["content"])
                        basic_analysis["ai_insights"] = ai_insights
                    except (KeyError, json.JSONDecodeError):
                        basic_analysis["ai_insights"] = {"error": "Could not parse AI analysis"}
            
            return Success(basic_analysis)
            
        except Exception as e:
            logger.error(f"Project analysis error: {e}")
            return Error(str(e))

    @method 
    async def ai_assisted_debugging(
        self, 
        error_message: str, 
        stack_trace: str, 
        file_path: str,
        project_path: str
    ):
        """AI-powered debugging assistance"""
        try:
            # Get file context
            try:
                with open(file_path, 'r') as f:
                    file_content = f.read()
            except:
                file_content = "Could not read file"
            
            # Get project context
            project_analysis = self.code_intelligence.analyze_project(project_path)
            
            debug_prompt = f"""
            You are an expert debugging assistant. Help debug this error:
            
            Error: {error_message}
            Stack Trace: {stack_trace}
            File: {file_path}
            
            Project Context:
            - Languages: {project_analysis.get('language_distribution', {})}
            - Total Symbols: {project_analysis.get('total_symbols', 0)}
            
            File Content (relevant section):
            {file_content[:2000]}
            
            Provide:
            1. Root cause analysis
            2. Step-by-step debugging approach
            3. Potential fixes with code examples
            4. Prevention strategies
            5. Related code patterns to check
            
            Return as structured JSON.
            """
            
            debug_result = await self.call_llm(
                debug_prompt,
                model="deepseek",
                task_type="complex",
                max_tokens=6000
            )
            
            if "error" not in debug_result:
                try:
                    debug_analysis = json.loads(debug_result["choices"][0]["message"]["content"])
                    return Success({
                        "debug_analysis": debug_analysis,
                        "project_context": project_analysis,
                        "file_analyzed": file_path
                    })
                except (KeyError, json.JSONDecodeError):
                    return Error("Could not parse debugging analysis")
            else:
                return Error(debug_result["error"])
                
        except Exception as e:
            logger.error(f"AI debugging error: {e}")
            return Error(str(e))

    @method
    async def code_generation(
        self,
        description: str,
        language: str,
        project_path: str,
        file_path: str = None,
        framework: str = None
    ):
        """AI-powered code generation"""
        try:
            # Get project context
            project_analysis = self.code_intelligence.analyze_project(project_path)
            
            # Get existing code context if file specified
            existing_code = ""
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    existing_code = f.read()
            
            generation_prompt = f"""
            Generate {language} code based on this description: {description}
            
            Project Context:
            - Main Languages: {project_analysis.get('language_distribution', {})}
            - Framework: {framework or 'None specified'}
            - Total Symbols: {project_analysis.get('total_symbols', 0)}
            
            Existing Code Context:
            {existing_code[:1500] if existing_code else 'New file'}
            
            Requirements:
            1. Follow project coding standards
            2. Include proper error handling
            3. Add comprehensive docstrings/comments
            4. Follow language best practices
            5. Ensure code is production-ready
            6. Include relevant imports
            
            Return the generated code with explanations.
            """
            
            generation_result = await self.call_llm(
                generation_prompt,
                model="deepseek",
                task_type="complex",
                max_tokens=8000
            )
            
            if "error" not in generation_result:
                generated_code = generation_result["choices"][0]["message"]["content"]
                return Success({
                    "generated_code": generated_code,
                    "language": language,
                    "project_context": project_analysis,
                    "target_file": file_path
                })
            else:
                return Error(generation_result["error"])
                
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return Error(str(e))

    async def initialize(self):
        """Initialize all components of the comprehensive MCP server"""
        logger.info("🚀 Initializing Comprehensive MCP Server...")
        
        # Initialize core components
        await self.initialize_database()
        await self.initialize_llm_clients()
        
        # Initialize project manager
        self.project_manager = ProjectManager(self.code_intelligence, self.db_pool)
        
        # Start MCP servers
        await self.start_mcp_servers()
        
        logger.info("✅ Comprehensive MCP Server fully initialized!")

    def setup_flask_routes(self):
        """Setup Flask routes for the comprehensive server"""
        
        @self.app.route("/", methods=["POST"])
        def handle_jsonrpc():
            """Handle JSON-RPC requests"""
            try:
                response = dispatch(request.get_data().decode())
                return jsonify(response)
            except Exception as e:
                logger.error(f"JSON-RPC dispatch error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/health", methods=["GET"])
        def health_check():
            """Comprehensive health check"""
            mcp_status = {}
            for name, config in self.mcp_server_configs.items():
                if config.enabled:
                    mcp_status[name] = "active" if name in self.server_processes or config.type == "builtin" else "inactive"
            
            return jsonify({
                "status": "healthy",
                "timestamp": time.time(),
                "components": {
                    "database": "connected" if self.db_pool else "disconnected",
                    "deepseek_llm": "connected (local)" if self.deepseek_client else "disconnected",
                    "granite_llm": "connected (local)" if self.granite_client else "disconnected",
                    "project_manager": "active" if self.project_manager else "inactive",
                    "code_intelligence": "loaded"
                },
                "mcp_servers": mcp_status,
                "total_tools": sum(len(config.tools or []) for config in self.mcp_server_configs.values() if config.enabled),
                "features": {
                    "comprehensive_completions": True,
                    "ai_debugging": True,
                    "code_generation": True,
                    "project_analysis": True,
                    "multi_llm_support": True,
                    "aggregated_mcp_servers": True
                }
            })

        @self.app.route("/api/servers", methods=["GET"])
        def list_servers():
            """List all MCP servers and their status"""
            servers = []
            for name, config in self.mcp_server_configs.items():
                servers.append({
                    "name": name,
                    "type": config.type,
                    "enabled": config.enabled,
                    "description": config.description,
                    "tools": config.tools or [],
                    "status": "running" if name in self.server_processes or config.type == "builtin" else "stopped"
                })
            return jsonify({"servers": servers})

# Global instance
comprehensive_server = ComprehensiveMCPServer()

# Register all methods dynamically
for method_name in dir(comprehensive_server):
    if method_name.startswith('__') or method_name in ['app', 'initialize', 'setup_flask_routes']:
        continue
    
    method_obj = getattr(comprehensive_server, method_name)
    if callable(method_obj) and hasattr(method_obj, '_jsonrpc_method_name'):
        globals()[method_name] = method_obj

if __name__ == "__main__":
    async def main():
        # Initialize the comprehensive server
        await comprehensive_server.initialize()
        
        # Setup Flask routes
        comprehensive_server.setup_flask_routes()
        
        # Start the server
        comprehensive_server.app.run(
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8080")),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )
    
    # Run the async initialization
    asyncio.run(main())