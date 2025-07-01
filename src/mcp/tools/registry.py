"""Tool registry for MCP server."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


@dataclass
class ToolDefinition:
    """Tool definition with metadata."""
    name: str
    description: str
    parameters: List[ToolParameter]
    handler: Callable[..., Awaitable[Any]]


class BaseTool(ABC):
    """Base class for MCP tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        pass


class ToolRegistry:
    """Registry for managing MCP tools."""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._initialized = False
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        definition = ToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
            handler=tool.execute
        )
        self.tools[tool.name] = definition
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self.tools.keys())
    
    async def call_tool(self, name: str, **kwargs) -> Any:
        """Call a tool with given parameters."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        
        # Validate required parameters
        provided_params = set(kwargs.keys())
        required_params = {p.name for p in tool.parameters if p.required}
        missing_params = required_params - provided_params
        
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")
        
        # Add default values for optional parameters
        for param in tool.parameters:
            if param.name not in kwargs and param.default is not None:
                kwargs[param.name] = param.default
        
        # Execute the tool
        try:
            result = await tool.handler(**kwargs)
            logger.info(f"Tool executed successfully: {name}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {name}", error=str(e))
            raise
    
    async def register_all_tools(self, db_manager, llm_manager) -> None:
        """Register all available tools."""
        if self._initialized:
            return
        
        # Import and register tools
        from .file_operations import FileReadTool, FileWriteTool, FileListTool
        from .memory_tools import StoreMemoryTool, SearchMemoryTool
        from .code_tools import CodeCompletionTool, ProjectAnalysisTool
        from .git_tools import GitStatusTool, GitCommitTool
        
        # File operations
        self.register_tool(FileReadTool())
        self.register_tool(FileWriteTool())
        self.register_tool(FileListTool())
        
        # Memory tools
        self.register_tool(StoreMemoryTool(db_manager, llm_manager))
        self.register_tool(SearchMemoryTool(db_manager, llm_manager))
        
        # Code intelligence
        self.register_tool(CodeCompletionTool(llm_manager))
        self.register_tool(ProjectAnalysisTool(db_manager))
        
        # Git operations
        self.register_tool(GitStatusTool())
        self.register_tool(GitCommitTool())
        
        self._initialized = True
        logger.info(f"Registered {len(self.tools)} tools")