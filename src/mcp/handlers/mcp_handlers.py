"""MCP protocol handlers."""

import time
from typing import Any, Dict, List, Optional

import structlog
from jsonrpcserver import Success, Error

logger = structlog.get_logger(__name__)


class MCPHandlers:
    """Handlers for MCP protocol methods."""
    
    def __init__(self):
        self.db_manager = None
        self.llm_manager = None
        self.tool_registry = None
        
    async def initialize(self, db_manager, llm_manager, tool_registry):
        """Initialize handlers with dependencies."""
        self.db_manager = db_manager
        self.llm_manager = llm_manager
        self.tool_registry = tool_registry
    
    async def tools_list(self) -> Success:
        """Handle tools/list request."""
        try:
            tools = []
            for name, definition in self.tool_registry.tools.items():
                tool_info = {
                    "name": name,
                    "description": definition.description,
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
                
                # Convert parameters to JSON schema format
                for param in definition.parameters:
                    tool_info["inputSchema"]["properties"][param.name] = {
                        "type": param.type,
                        "description": param.description
                    }
                    if param.default is not None:
                        tool_info["inputSchema"]["properties"][param.name]["default"] = param.default
                    if param.required:
                        tool_info["inputSchema"]["required"].append(param.name)
                
                tools.append(tool_info)
            
            return Success({"tools": tools})
            
        except Exception as e:
            logger.error("Failed to list tools", error=str(e))
            return Error("Failed to list tools")
    
    async def tools_call(self, name: str, arguments: Dict[str, Any]) -> Success:
        """Handle tools/call request."""
        start_time = time.time()
        
        try:
            # Log the tool call
            session_id = arguments.get("_session_id", "unknown")
            
            # Execute the tool
            result = await self.tool_registry.call_tool(name, **arguments)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log to database if available
            if self.db_manager:
                try:
                    from ...core.database import ToolCallRepository
                    tool_call_repo = ToolCallRepository(self.db_manager)
                    await tool_call_repo.log_tool_call(
                        session_id=session_id,
                        tool_name=name,
                        parameters=arguments,
                        result=result,
                        success="error" not in result,
                        error_message=result.get("error"),
                        duration_ms=duration_ms
                    )
                except Exception as e:
                    logger.warning("Failed to log tool call", error=str(e))
            
            return Success({
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            })
            
        except Exception as e:
            logger.error(f"Tool call failed: {name}", error=str(e))
            return Error(f"Tool call failed: {str(e)}")
    
    async def resources_list(self) -> Success:
        """Handle resources/list request."""
        try:
            # Basic resources - could be expanded
            resources = [
                {
                    "uri": "file://workspace",
                    "name": "Workspace Files",
                    "description": "Access to workspace file system",
                    "mimeType": "application/octet-stream"
                },
                {
                    "uri": "memory://sessions",
                    "name": "Session Memories",
                    "description": "Access to stored conversation memories",
                    "mimeType": "application/json"
                }
            ]
            
            return Success({"resources": resources})
            
        except Exception as e:
            logger.error("Failed to list resources", error=str(e))
            return Error("Failed to list resources")
    
    async def resources_read(self, uri: str) -> Success:
        """Handle resources/read request."""
        try:
            if uri.startswith("file://"):
                # File resource
                file_path = uri[7:]  # Remove "file://" prefix
                
                from ...tools.file_operations import FileReadTool
                file_tool = FileReadTool()
                result = await file_tool.execute(file_path=file_path)
                
                if "error" in result:
                    return Error(result["error"])
                
                return Success({
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/plain",
                            "text": result["content"]
                        }
                    ]
                })
                
            elif uri.startswith("memory://"):
                # Memory resource
                return Success({
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": '{"message": "Memory access not implemented in basic version"}'
                        }
                    ]
                })
            else:
                return Error(f"Unsupported resource URI: {uri}")
                
        except Exception as e:
            logger.error(f"Failed to read resource: {uri}", error=str(e))
            return Error(f"Failed to read resource: {str(e)}")
    
    async def prompts_list(self) -> Success:
        """Handle prompts/list request."""
        try:
            prompts = [
                {
                    "name": "code_review",
                    "description": "Review code for quality and potential issues",
                    "arguments": [
                        {
                            "name": "code",
                            "description": "Code to review",
                            "required": True
                        },
                        {
                            "name": "language",
                            "description": "Programming language",
                            "required": False
                        }
                    ]
                },
                {
                    "name": "explain_code",
                    "description": "Explain what a piece of code does",
                    "arguments": [
                        {
                            "name": "code",
                            "description": "Code to explain",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "debug_help",
                    "description": "Help debug an issue",
                    "arguments": [
                        {
                            "name": "error_message",
                            "description": "Error message or description",
                            "required": True
                        },
                        {
                            "name": "context",
                            "description": "Additional context",
                            "required": False
                        }
                    ]
                }
            ]
            
            return Success({"prompts": prompts})
            
        except Exception as e:
            logger.error("Failed to list prompts", error=str(e))
            return Error("Failed to list prompts")
    
    async def prompts_get(self, name: str, arguments: Dict[str, Any]) -> Success:
        """Handle prompts/get request."""
        try:
            if name == "code_review":
                code = arguments.get("code", "")
                language = arguments.get("language", "unknown")
                
                prompt = f"""Please review the following {language} code for:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance improvements
4. Security considerations
5. Readability and maintainability

Code:
```{language}
{code}
```

Provide specific, actionable feedback."""
                
            elif name == "explain_code":
                code = arguments.get("code", "")
                
                prompt = f"""Please explain what this code does:

```
{code}
```

Include:
- Overall purpose
- How it works step by step
- Key components and their roles
- Any notable patterns or techniques used"""
                
            elif name == "debug_help":
                error_message = arguments.get("error_message", "")
                context = arguments.get("context", "")
                
                prompt = f"""Help debug this issue:

Error: {error_message}

Context: {context}

Please provide:
1. Likely causes of this error
2. Steps to diagnose the problem
3. Potential solutions
4. Prevention strategies"""
                
            else:
                return Error(f"Unknown prompt: {name}")
            
            return Success({
                "description": f"Generated prompt for {name}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": prompt
                        }
                    }
                ]
            })
            
        except Exception as e:
            logger.error(f"Failed to get prompt: {name}", error=str(e))
            return Error(f"Failed to get prompt: {str(e)}")