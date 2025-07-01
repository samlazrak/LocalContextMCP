"""
Basic tests for MCP Server functionality.
Demonstrates testing patterns and validates core components.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path

# These imports will work once dependencies are installed
try:
    from mcp_server.config import get_config
    from mcp_server.tools.filesystem import ReadFileTool, WriteFileTool
    from mcp_server.tools.base import ToolResult
    from mcp_server.database.models import MCPSession, ToolCall
except ImportError:
    # Skip tests if dependencies not installed
    pytest.skip("Dependencies not installed", allow_module_level=True)


class TestConfiguration:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test that configuration initializes with defaults."""
        config = get_config()
        
        assert config.environment in ["development", "staging", "production"]
        assert config.server.port == 8080
        assert config.database.host == "localhost"
        assert config.llm.default_provider in ["lmstudio", "ollama", "openai"]
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = get_config()
        
        # Test environment validation
        assert config.is_development() or config.is_production()
        
        # Test security settings
        assert isinstance(config.tools.fs_allowed_paths, list)
        assert len(config.tools.fs_allowed_paths) > 0


class TestDatabaseModels:
    """Test database models."""
    
    def test_mcp_session_creation(self):
        """Test MCP session model creation."""
        session = MCPSession(
            session_id="test-session",
            user_id="test-user",
            project_path="/workspace"
        )
        
        assert session.session_id == "test-session"
        assert session.user_id == "test-user"
        assert session.project_path == "/workspace"
        assert session.metadata == {}
        assert session.created_at is not None
        assert session.last_activity is not None
    
    def test_tool_call_creation(self):
        """Test tool call model creation."""
        tool_call = ToolCall(
            session_id="test-session",
            tool_name="readfile",
            parameters={"file_path": "/test.txt"},
            success=True
        )
        
        assert tool_call.session_id == "test-session"
        assert tool_call.tool_name == "readfile"
        assert tool_call.parameters == {"file_path": "/test.txt"}
        assert tool_call.result == {}
        assert tool_call.success is True
        assert tool_call.created_at is not None


class TestFileSystemTools:
    """Test filesystem tools."""
    
    @pytest.fixture
    def read_tool(self):
        """Create ReadFileTool instance."""
        return ReadFileTool()
    
    @pytest.fixture
    def write_tool(self):
        """Create WriteFileTool instance."""
        return WriteFileTool()
    
    def test_read_tool_properties(self, read_tool):
        """Test ReadFileTool properties."""
        assert read_tool.name == "readfile"
        assert "Read the contents of a file" in read_tool.description
        
        params = read_tool.parameters
        assert len(params) >= 1
        assert any(p.name == "file_path" for p in params)
        
        schema = read_tool.get_parameter_schema()
        assert schema["type"] == "object"
        assert "file_path" in schema["properties"]
        assert "file_path" in schema["required"]
    
    def test_write_tool_properties(self, write_tool):
        """Test WriteFileTool properties."""
        assert write_tool.name == "writefile"
        assert "Write content to a file" in write_tool.description
        
        params = write_tool.parameters
        assert len(params) >= 2
        assert any(p.name == "file_path" for p in params)
        assert any(p.name == "content" for p in params)
        
        schema = write_tool.get_parameter_schema()
        assert schema["type"] == "object"
        assert "file_path" in schema["properties"]
        assert "content" in schema["properties"]
    
    def test_parameter_validation(self, read_tool):
        """Test parameter validation."""
        # Valid parameters
        valid_params = read_tool.validate_parameters(
            file_path="/workspace/test.txt",
            encoding="utf-8"
        )
        assert valid_params["file_path"] == "/workspace/test.txt"
        assert valid_params["encoding"] == "utf-8"
        
        # Missing required parameter
        with pytest.raises(ValueError, match="Required parameter"):
            read_tool.validate_parameters(encoding="utf-8")
    
    @pytest.mark.asyncio
    async def test_read_file_execution(self, read_tool, tmp_path):
        """Test file reading execution."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, MCP Server!"
        test_file.write_text(test_content)
        
        # Mock path validation to allow temp directory
        with patch.object(read_tool, '_validate_path', return_value=test_file):
            result = await read_tool.execute(
                file_path=str(test_file),
                encoding="utf-8"
            )
        
        assert result.success is True
        assert result.data["content"] == test_content
        assert result.data["encoding"] == "utf-8"
        assert "file_info" in result.data
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, read_tool):
        """Test reading nonexistent file."""
        nonexistent_path = Path("/workspace/nonexistent.txt")
        
        with patch.object(read_tool, '_validate_path', return_value=nonexistent_path):
            result = await read_tool.execute(file_path=str(nonexistent_path))
        
        assert result.success is False
        assert "does not exist" in result.error_message
    
    @pytest.mark.asyncio
    async def test_write_file_execution(self, write_tool, tmp_path):
        """Test file writing execution."""
        test_file = tmp_path / "output.txt"
        test_content = "Hello from MCP Server!"
        
        # Mock path validation to allow temp directory
        with patch.object(write_tool, '_validate_path', return_value=test_file):
            result = await write_tool.execute(
                file_path=str(test_file),
                content=test_content,
                encoding="utf-8"
            )
        
        assert result.success is True
        assert result.data["bytes_written"] == len(test_content.encode())
        assert result.data["encoding"] == "utf-8"
        
        # Verify file was written
        assert test_file.exists()
        assert test_file.read_text() == test_content


class TestToolRegistry:
    """Test tool registry functionality."""
    
    def test_tool_registration(self):
        """Test tool registration."""
        from mcp_server.tools.base import ToolRegistry
        
        registry = ToolRegistry()
        read_tool = ReadFileTool()
        
        # Register tool
        registry.register(read_tool)
        
        # Check registration
        assert "readfile" in registry.list_tools()
        assert registry.get_tool("readfile") is read_tool
        
        # Get tool info
        tools_info = registry.get_all_tools_info()
        assert len(tools_info) == 1
        assert tools_info[0]["name"] == "readfile"
    
    @pytest.mark.asyncio
    async def test_tool_execution_via_registry(self):
        """Test tool execution through registry."""
        from mcp_server.tools.base import ToolRegistry
        
        registry = ToolRegistry()
        read_tool = ReadFileTool()
        registry.register(read_tool)
        
        # Mock the tool execution
        mock_result = ToolResult(success=True, data={"test": "data"})
        with patch.object(read_tool, 'run', return_value=mock_result) as mock_run:
            result = await registry.execute_tool(
                "readfile", 
                "test-session",
                file_path="/workspace/test.txt"
            )
        
        assert result.success is True
        mock_run.assert_called_once_with("test-session", file_path="/workspace/test.txt")
    
    @pytest.mark.asyncio
    async def test_unknown_tool_execution(self):
        """Test execution of unknown tool."""
        from mcp_server.tools.base import ToolRegistry
        
        registry = ToolRegistry()
        
        result = await registry.execute_tool("unknown_tool", "test-session")
        
        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message


# Integration test example
class TestServerIntegration:
    """Integration tests for server components."""
    
    @pytest.mark.asyncio
    async def test_basic_server_workflow(self):
        """Test basic server workflow with mocked dependencies."""
        # This would be expanded with actual server testing
        # using test clients and mocked external dependencies
        
        # Mock database operations
        with patch('mcp_server.database.connection.db_manager') as mock_db:
            mock_db.fetchrow.return_value = None  # No existing session
            mock_db.execute.return_value = "INSERT 0 1"
            
            # Mock session creation
            from mcp_server.server import get_or_create_session
            session_id = await get_or_create_session()
            
            assert session_id is not None
            assert len(session_id) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])