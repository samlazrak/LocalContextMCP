"""
Main MCP Server implementation using FastAPI.
Provides MCP protocol endpoints and integrates all server components.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import get_config
from .utils.logging import setup_logging, get_logger
from .database.connection import db_manager
from .database.models import DATABASE_SCHEMA, MCPSession
from .llm.client import llm_client
from .tools.base import tool_registry, ToolResult
from .tools.filesystem import (
    ReadFileTool, WriteFileTool, ListDirectoryTool, 
    CreateDirectoryTool, DeleteFileTool
)

# Initialize logging
config = get_config()
setup_logging(
    level=config.logging.level,
    format_type=config.logging.format,
    file_path=config.logging.file_path if config.logging.file_enabled else None,
    file_max_size=config.logging.file_max_size,
    file_backup_count=config.logging.file_backup_count
)

logger = get_logger(__name__)


# Pydantic models for API
class MCPRequest(BaseModel):
    """Base MCP request model."""
    jsonrpc: str = Field(default="2.0")
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """Base MCP response model."""
    jsonrpc: str = Field(default="2.0")
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class ToolCallRequest(BaseModel):
    """Tool call request model."""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class LLMCompletionRequest(BaseModel):
    """LLM completion request model."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting MCP Server")
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        # Create database schema
        await db_manager.execute(DATABASE_SCHEMA)
        logger.info("Database schema initialized")
        
        # Initialize LLM client
        await llm_client.initialize()
        
        # Register filesystem tools
        tool_registry.register(ReadFileTool())
        tool_registry.register(WriteFileTool())
        tool_registry.register(ListDirectoryTool())
        tool_registry.register(CreateDirectoryTool())
        tool_registry.register(DeleteFileTool())
        
        logger.info(
            "MCP Server initialized",
            tools=tool_registry.list_tools(),
            llm_providers=llm_client.get_available_providers()
        )
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize MCP Server", error=str(e))
        raise
    
    finally:
        # Cleanup
        logger.info("Shutting down MCP Server")
        await llm_client.close()
        await db_manager.close()


# Create FastAPI app
app = FastAPI(
    title="MCP Server",
    description="A comprehensive Model Context Protocol server",
    version="1.0.0",
    docs_url="/docs" if config.server.enable_docs else None,
    redoc_url="/redoc" if config.server.enable_docs else None,
    lifespan=lifespan
)

# Add CORS middleware
if config.server.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Helper functions
async def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create new one."""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Check if session exists
    existing = await db_manager.fetchrow(
        "SELECT session_id FROM mcp_sessions WHERE session_id = $1",
        session_id
    )
    
    if not existing:
        # Create new session
        session = MCPSession(session_id=session_id)
        await db_manager.execute(
            """
            INSERT INTO mcp_sessions (session_id, user_id, project_path, metadata, created_at, last_activity)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            session.session_id,
            session.user_id,
            session.project_path,
            session.metadata,
            session.created_at,
            session.last_activity
        )
        logger.info("Created new MCP session", session_id=session_id)
    
    return session_id


def create_mcp_response(result: Any, request_id: Optional[str] = None) -> MCPResponse:
    """Create MCP response."""
    return MCPResponse(result=result, id=request_id)


def create_mcp_error(message: str, code: int = -1, request_id: Optional[str] = None) -> MCPResponse:
    """Create MCP error response."""
    return MCPResponse(
        error={
            "code": code,
            "message": message
        },
        id=request_id
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database
        db_health = await db_manager.health_check()
        
        # Check LLM providers
        llm_health = await llm_client.health_check()
        
        # Overall health
        overall_healthy = (
            db_health.get("status") == "healthy" and
            any(
                provider.get("status") == "healthy"
                for provider in llm_health.get("providers", {}).values()
            )
        )
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": time.time(),
            "components": {
                "database": db_health,
                "llm": llm_health,
                "tools": {
                    "status": "healthy",
                    "available_tools": tool_registry.list_tools()
                }
            }
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# MCP Protocol endpoints

@app.post("/mcp")
async def mcp_handler(request: MCPRequest) -> MCPResponse:
    """Main MCP protocol handler."""
    try:
        logger.debug("Received MCP request", method=request.method, id=request.id)
        
        # Route to appropriate handler
        if request.method == "tools/list":
            return await handle_tools_list(request)
        elif request.method == "tools/call":
            return await handle_tools_call(request)
        elif request.method == "completion/complete":
            return await handle_completion(request)
        elif request.method == "session/create":
            return await handle_session_create(request)
        elif request.method == "session/info":
            return await handle_session_info(request)
        else:
            return create_mcp_error(f"Unknown method: {request.method}", -32601, request.id)
    
    except Exception as e:
        logger.error("MCP request failed", method=request.method, error=str(e))
        return create_mcp_error(str(e), -32603, request.id)


async def handle_tools_list(request: MCPRequest) -> MCPResponse:
    """Handle tools/list method."""
    tools_info = tool_registry.get_all_tools_info()
    return create_mcp_response({"tools": tools_info}, request.id)


async def handle_tools_call(request: MCPRequest) -> MCPResponse:
    """Handle tools/call method."""
    if not request.params:
        return create_mcp_error("Missing parameters", -32602, request.id)
    
    tool_name = request.params.get("name")
    arguments = request.params.get("arguments", {})
    session_id = request.params.get("session_id")
    
    if not tool_name:
        return create_mcp_error("Missing tool name", -32602, request.id)
    
    # Ensure session exists
    session_id = await get_or_create_session(session_id)
    
    # Execute tool
    result = await tool_registry.execute_tool(tool_name, session_id, **arguments)
    
    return create_mcp_response({
        "content": [
            {
                "type": "text",
                "text": json.dumps(result.to_dict(), indent=2)
            }
        ]
    }, request.id)


async def handle_completion(request: MCPRequest) -> MCPResponse:
    """Handle completion/complete method."""
    if not request.params:
        return create_mcp_error("Missing parameters", -32602, request.id)
    
    messages = request.params.get("messages", [])
    model = request.params.get("model")
    temperature = request.params.get("temperature")
    max_tokens = request.params.get("max_tokens")
    
    if not messages:
        return create_mcp_error("Missing messages", -32602, request.id)
    
    try:
        # Call LLM
        kwargs = {}
        if model:
            kwargs["model"] = model
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = await llm_client.complete(messages, **kwargs)
        
        return create_mcp_response({
            "content": response.content,
            "model": response.model,
            "usage": response.usage,
            "finish_reason": response.finish_reason
        }, request.id)
        
    except Exception as e:
        return create_mcp_error(f"LLM completion failed: {e}", -32603, request.id)


async def handle_session_create(request: MCPRequest) -> MCPResponse:
    """Handle session/create method."""
    session_id = await get_or_create_session()
    return create_mcp_response({"session_id": session_id}, request.id)


async def handle_session_info(request: MCPRequest) -> MCPResponse:
    """Handle session/info method."""
    if not request.params:
        return create_mcp_error("Missing parameters", -32602, request.id)
    
    session_id = request.params.get("session_id")
    if not session_id:
        return create_mcp_error("Missing session_id", -32602, request.id)
    
    # Get session info
    session_row = await db_manager.fetchrow(
        "SELECT * FROM mcp_sessions WHERE session_id = $1",
        session_id
    )
    
    if not session_row:
        return create_mcp_error("Session not found", -32603, request.id)
    
    # Get recent tool calls
    tool_calls = await db_manager.fetch(
        """
        SELECT tool_name, success, created_at, duration_ms
        FROM mcp_tool_calls 
        WHERE session_id = $1 
        ORDER BY created_at DESC 
        LIMIT 10
        """,
        session_id
    )
    
    return create_mcp_response({
        "session": dict(session_row),
        "recent_tool_calls": [dict(call) for call in tool_calls]
    }, request.id)


# REST API endpoints for easier testing

@app.post("/api/v1/tools/call")
async def rest_tool_call(request: ToolCallRequest):
    """REST endpoint for tool calls."""
    session_id = await get_or_create_session(request.session_id)
    result = await tool_registry.execute_tool(
        request.tool_name, 
        session_id, 
        **request.parameters
    )
    return result.to_dict()


@app.get("/api/v1/tools")
async def rest_list_tools():
    """REST endpoint to list tools."""
    return {"tools": tool_registry.get_all_tools_info()}


@app.post("/api/v1/llm/complete")
async def rest_llm_complete(request: LLMCompletionRequest):
    """REST endpoint for LLM completion."""
    try:
        kwargs = {}
        if request.model:
            kwargs["model"] = request.model
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        if request.stream:
            return StreamingResponse(
                stream_llm_completion(request.messages, **kwargs),
                media_type="text/plain"
            )
        else:
            response = await llm_client.complete(request.messages, **kwargs)
            return {
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
                "finish_reason": response.finish_reason,
                "response_time_ms": response.response_time_ms
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def stream_llm_completion(messages: List[Dict[str, str]], **kwargs):
    """Stream LLM completion chunks."""
    try:
        async for chunk in llm_client.stream_complete(messages, **kwargs):
            yield f"data: {json.dumps({'content': chunk.content})}\n\n"
            
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.get("/api/v1/status")
async def rest_status():
    """REST endpoint for server status."""
    return await health_check()


# Add middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP requests."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "HTTP request",
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params)
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start_time
    logger.info(
        "HTTP response",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )
    
    return response


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "mcp_server.server:app",
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
        reload=config.is_development(),
        log_level=config.logging.level.lower()
    )