"""Main MCP server implementation."""

import asyncio
import time
import traceback
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from jsonrpcserver import method, Success, Error, dispatch_to_response_json

from ..core.database import (
    DatabaseManager, SessionRepository, ToolCallRepository,
    initialize_database, close_database, get_database
)
from ..core.llm_client import initialize_llm_clients, LLMManager, get_llm_manager
from ..core.config import get_settings
from .tools.registry import ToolRegistry
from .handlers.mcp_handlers import MCPHandlers

logger = structlog.get_logger(__name__)


class MCPServer:
    """Main MCP server class."""
    
    def __init__(self):
        self.settings = get_settings()
        self.app = FastAPI(
            title="LocalContextMCP",
            description="Model Context Protocol server with intelligence features",
            version="1.0.0"
        )
        
        # Core components
        self.db: Optional[DatabaseManager] = None
        self.llm_manager: Optional[LLMManager] = None
        self.tool_registry = ToolRegistry()
        self.handlers = MCPHandlers()
        
        # Repositories
        self.session_repo: Optional[SessionRepository] = None
        self.tool_call_repo: Optional[ToolCallRepository] = None
        
        # Setup routes
        self._setup_routes()
        
    async def initialize(self) -> None:
        """Initialize the MCP server."""
        logger.info("Initializing MCP server...")
        
        try:
            # Initialize database
            await initialize_database()
            self.db = await get_database()
            
            # Initialize repositories
            self.session_repo = SessionRepository(self.db)
            self.tool_call_repo = ToolCallRepository(self.db)
            
            # Initialize LLM clients
            await initialize_llm_clients()
            self.llm_manager = await get_llm_manager()
            
            # Register tools
            await self.tool_registry.register_all_tools(self.db, self.llm_manager)
            
            # Initialize handlers
            await self.handlers.initialize(
                self.db, self.llm_manager, self.tool_registry
            )
            
            logger.info("MCP server initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize MCP server", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the MCP server."""
        logger.info("Shutting down MCP server...")
        await close_database()
        logger.info("MCP server shutdown complete")
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                # Check database
                db_healthy = self.db is not None
                if self.db:
                    # Simple query to test connection
                    await self.db.fetchval("SELECT 1")
                
                # Check LLM providers
                llm_health = {}
                if self.llm_manager:
                    llm_health = await self.llm_manager.health_check_all()
                
                return {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "database": db_healthy,
                    "llm_providers": llm_health,
                    "tools_count": len(self.tool_registry.tools)
                }
            except Exception as e:
                logger.error("Health check failed", error=str(e))
                raise HTTPException(status_code=503, detail="Service unhealthy")
        
        @self.app.post("/mcp")
        async def handle_mcp_request(request: Request):
            """Handle MCP JSON-RPC requests."""
            try:
                body = await request.body()
                response = dispatch_to_response_json(
                    body.decode(),
                    [
                        self.handlers.tools_list,
                        self.handlers.tools_call,
                        self.handlers.resources_list,
                        self.handlers.resources_read,
                        self.handlers.prompts_list,
                        self.handlers.prompts_get
                    ]
                )
                return JSONResponse(content=response)
            except Exception as e:
                logger.error("MCP request failed", error=str(e))
                return JSONResponse(
                    content={"error": str(e)},
                    status_code=500
                )
        
        @self.app.get("/api/sessions")
        async def list_sessions():
            """List active sessions."""
            if not self.session_repo:
                raise HTTPException(status_code=503, detail="Server not initialized")
            
            sessions = await self.session_repo.list_active_sessions()
            return {"sessions": sessions}
        
        @self.app.post("/api/sessions")
        async def create_session(session_data: Dict[str, Any]):
            """Create a new session."""
            if not self.session_repo:
                raise HTTPException(status_code=503, detail="Server not initialized")
            
            session = await self.session_repo.create_session(
                session_id=session_data.get("session_id"),
                user_id=session_data.get("user_id"),
                project_path=session_data.get("project_path"),
                metadata=session_data.get("metadata", {})
            )
            return {"session": session}
        
        @self.app.get("/api/tools")
        async def list_tools():
            """List available tools."""
            tools = [
                {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
                for name, tool in self.tool_registry.tools.items()
            ]
            return {"tools": tools}
        
        @self.app.get("/api/stats")
        async def get_stats():
            """Get server statistics."""
            if not self.tool_call_repo:
                raise HTTPException(status_code=503, detail="Server not initialized")
            
            stats = await self.tool_call_repo.get_tool_usage_stats()
            return {"stats": stats}


# Global MCP methods for JSON-RPC (delegated to handlers)
mcp_server = MCPServer()


@method
async def tools_list():
    """MCP tools/list method."""
    return await mcp_server.handlers.tools_list()


@method
async def tools_call(name: str, arguments: Dict[str, Any] = None):
    """MCP tools/call method."""
    return await mcp_server.handlers.tools_call(name, arguments or {})


@method
async def resources_list():
    """MCP resources/list method."""
    return await mcp_server.handlers.resources_list()


@method
async def resources_read(uri: str):
    """MCP resources/read method."""
    return await mcp_server.handlers.resources_read(uri)


@method
async def prompts_list():
    """MCP prompts/list method."""
    return await mcp_server.handlers.prompts_list()


@method
async def prompts_get(name: str, arguments: Dict[str, Any] = None):
    """MCP prompts/get method."""
    return await mcp_server.handlers.prompts_get(name, arguments or {})


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return mcp_server.app


async def run_server():
    """Run the MCP server."""
    import uvicorn
    
    await mcp_server.initialize()
    
    try:
        config = uvicorn.Config(
            app=mcp_server.app,
            host=mcp_server.settings.server.host,
            port=mcp_server.settings.server.port,
            log_level=mcp_server.settings.server.log_level.lower(),
            loop="asyncio"
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await mcp_server.shutdown()


if __name__ == "__main__":
    asyncio.run(run_server())