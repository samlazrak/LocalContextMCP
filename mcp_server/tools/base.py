"""
Base tool class for MCP Server tools.
Provides common functionality and interface for all tools.
"""

import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from ..utils.logging import get_logger
from ..database.models import ToolCall
from ..database.connection import db_manager

logger = get_logger(__name__)


@dataclass
class ToolParameter:
    """Represents a tool parameter definition."""
    name: str
    type: str  # string, integer, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""
    success: bool
    data: Any = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "metadata": self.metadata or {}
        }


class MCPTool(ABC):
    """Abstract base class for all MCP tools."""
    
    def __init__(self):
        self.name = self.__class__.__name__.lower().replace('tool', '')
        self.logger = get_logger(f"tools.{self.name}")
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get tool description."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Get tool parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters."""
        properties = {}
        required = []
        
        for param in self.parameters:
            param_schema = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                param_schema["enum"] = param.enum
            
            if param.default is not None:
                param_schema["default"] = param.default
            
            properties[param.name] = param_schema
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and sanitize input parameters."""
        validated = {}
        
        for param in self.parameters:
            value = kwargs.get(param.name)
            
            # Check required parameters
            if param.required and value is None:
                raise ValueError(f"Required parameter '{param.name}' is missing")
            
            # Use default value if provided
            if value is None and param.default is not None:
                value = param.default
            
            # Type validation
            if value is not None:
                validated[param.name] = self._validate_parameter_type(param, value)
            
        return validated
    
    def _validate_parameter_type(self, param: ToolParameter, value: Any) -> Any:
        """Validate parameter type."""
        if param.type == "string":
            if not isinstance(value, str):
                return str(value)
        elif param.type == "integer":
            if not isinstance(value, int):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Parameter '{param.name}' must be an integer")
        elif param.type == "boolean":
            if not isinstance(value, bool):
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                return bool(value)
        elif param.type == "array":
            if not isinstance(value, list):
                raise ValueError(f"Parameter '{param.name}' must be an array")
        elif param.type == "object":
            if not isinstance(value, dict):
                raise ValueError(f"Parameter '{param.name}' must be an object")
        
        # Enum validation
        if param.enum and value not in param.enum:
            raise ValueError(f"Parameter '{param.name}' must be one of: {param.enum}")
        
        return value
    
    async def run(self, session_id: str, **kwargs) -> ToolResult:
        """
        Run the tool with logging and error handling.
        
        Args:
            session_id: MCP session ID
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with execution results
        """
        start_time = time.time()
        
        # Log tool execution start
        self.logger.info(
            f"Starting tool execution: {self.name}",
            session_id=session_id,
            parameters=kwargs
        )
        
        try:
            # Validate parameters
            validated_params = self.validate_parameters(**kwargs)
            
            # Execute the tool
            result = await self.execute(**validated_params)
            
            # Calculate execution time
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log successful execution
            self.logger.info(
                f"Tool execution completed: {self.name}",
                session_id=session_id,
                success=result.success,
                duration_ms=duration_ms
            )
            
            # Store tool call in database
            await self._store_tool_call(
                session_id=session_id,
                parameters=validated_params,
                result=result.to_dict(),
                duration_ms=duration_ms,
                success=result.success,
                error_message=result.error_message
            )
            
            return result
            
        except Exception as e:
            # Calculate execution time
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            self.logger.error(
                f"Tool execution failed: {self.name}",
                session_id=session_id,
                error=str(e),
                duration_ms=duration_ms
            )
            
            # Create error result
            error_result = ToolResult(
                success=False,
                error_message=str(e),
                metadata={"execution_time_ms": duration_ms}
            )
            
            # Store failed tool call in database
            await self._store_tool_call(
                session_id=session_id,
                parameters=kwargs,
                result=error_result.to_dict(),
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
            
            return error_result
    
    async def _store_tool_call(
        self,
        session_id: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        duration_ms: int,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """Store tool call in database."""
        try:
            tool_call = ToolCall(
                session_id=session_id,
                tool_name=self.name,
                server_name="mcp_server",
                parameters=parameters,
                result=result,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message
            )
            
            await db_manager.execute(
                """
                INSERT INTO mcp_tool_calls 
                (session_id, tool_name, server_name, parameters, result, 
                 duration_ms, success, error_message, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                tool_call.session_id,
                tool_call.tool_name,
                tool_call.server_name,
                tool_call.parameters,
                tool_call.result,
                tool_call.duration_ms,
                tool_call.success,
                tool_call.error_message,
                tool_call.created_at
            )
            
        except Exception as e:
            # Don't fail the tool execution if logging fails
            self.logger.warning(
                "Failed to store tool call in database",
                error=str(e),
                tool_name=self.name
            )
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get complete tool information."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameter_schema(),
            "metadata": {
                "class": self.__class__.__name__,
                "module": self.__class__.__module__
            }
        }


class ToolRegistry:
    """Registry for managing MCP tools."""
    
    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
        self.logger = get_logger("tools.registry")
    
    def register(self, tool: MCPTool) -> None:
        """Register a tool."""
        if tool.name in self.tools:
            self.logger.warning(f"Tool '{tool.name}' is already registered, overriding")
        
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
    
    def unregister(self, tool_name: str) -> None:
        """Unregister a tool."""
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.logger.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self.tools.keys())
    
    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """Get information about all registered tools."""
        return [tool.get_tool_info() for tool in self.tools.values()]
    
    async def execute_tool(
        self, 
        tool_name: str, 
        session_id: str, 
        **kwargs
    ) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get_tool(tool_name)
        
        if not tool:
            error_msg = f"Tool '{tool_name}' not found"
            self.logger.error(error_msg, available_tools=self.list_tools())
            return ToolResult(
                success=False,
                error_message=error_msg
            )
        
        return await tool.run(session_id, **kwargs)


# Global tool registry
tool_registry = ToolRegistry()


def register_tool(tool: MCPTool) -> None:
    """Register a tool with the global registry."""
    tool_registry.register(tool)


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return tool_registry