"""Pytest configuration and fixtures for LocalContextMCP tests."""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Import the modules we want to test
# Note: These imports may fail due to missing dependencies in the linter environment
# but will work when the actual dependencies are installed
try:
    from src.core.config import Settings
    from src.core.database import DatabaseManager
    from src.core.llm_client import LLMManager
    from src.mcp.tools.registry import ToolRegistry
except ImportError:
    # Mock imports for testing environment
    Settings = None
    DatabaseManager = None
    LLMManager = None
    ToolRegistry = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.database.url = "postgresql://test:test@localhost:5432/test_db"
    settings.database.pool_size = 5
    settings.database.pool_timeout = 30
    
    settings.lmstudio.base_url = "http://localhost:1234/v1"
    settings.lmstudio.model = "test-model"
    settings.lmstudio.embedding_model = "test-embedding-model"
    settings.lmstudio.timeout = 30
    
    settings.server.host = "0.0.0.0"
    settings.server.port = 8080
    settings.server.log_level = "INFO"
    
    return settings


@pytest_asyncio.fixture
async def mock_database() -> AsyncGenerator[MagicMock, None]:
    """Mock database manager for testing."""
    db = MagicMock()
    db.pool = MagicMock()
    
    # Mock async methods
    db.initialize = AsyncMock()
    db.close = AsyncMock()
    db.execute = AsyncMock(return_value="SUCCESS")
    db.fetch = AsyncMock(return_value=[])
    db.fetchrow = AsyncMock(return_value=None)
    db.fetchval = AsyncMock(return_value=1)
    
    yield db


@pytest_asyncio.fixture
async def mock_llm_manager() -> AsyncGenerator[MagicMock, None]:
    """Mock LLM manager for testing."""
    llm = MagicMock()
    
    # Mock async methods
    llm.initialize = AsyncMock()
    llm.chat_completion = AsyncMock(return_value=MagicMock(
        content="Test response",
        model="test-model",
        usage={"tokens": 100},
        finish_reason="stop",
        response_time_ms=100,
        provider="test"
    ))
    llm.embedding = AsyncMock(return_value=MagicMock(
        embedding=[0.1, 0.2, 0.3],
        model="test-embedding-model",
        usage={"tokens": 50},
        response_time_ms=50,
        provider="test"
    ))
    llm.health_check_all = AsyncMock(return_value={"test": True})
    
    yield llm


@pytest.fixture
def mock_tool_registry(mock_database, mock_llm_manager):
    """Mock tool registry for testing."""
    registry = MagicMock()
    registry.tools = {}
    registry.register_tool = MagicMock()
    registry.get_tool = MagicMock(return_value=None)
    registry.list_tools = MagicMock(return_value=[])
    registry.call_tool = AsyncMock(return_value={"result": "success"})
    registry.register_all_tools = AsyncMock()
    
    return registry


@pytest_asyncio.fixture
async def mock_session_repo(mock_database) -> AsyncGenerator[MagicMock, None]:
    """Mock session repository for testing."""
    repo = MagicMock()
    
    repo.create_session = AsyncMock(return_value={
        "id": 1,
        "session_id": "test_session",
        "user_id": "test_user",
        "project_path": "/test/path",
        "metadata": {},
        "created_at": "2024-01-01T00:00:00Z",
        "is_active": True
    })
    
    repo.get_session = AsyncMock(return_value={
        "id": 1,
        "session_id": "test_session",
        "user_id": "test_user",
        "project_path": "/test/path",
        "metadata": {},
        "created_at": "2024-01-01T00:00:00Z",
        "is_active": True
    })
    
    repo.update_activity = AsyncMock()
    repo.list_active_sessions = AsyncMock(return_value=[])
    
    yield repo


@pytest_asyncio.fixture
async def mock_memory_repo(mock_database) -> AsyncGenerator[MagicMock, None]:
    """Mock memory repository for testing."""
    repo = MagicMock()
    
    repo.store_memory = AsyncMock(return_value=1)
    repo.search_memories_text = AsyncMock(return_value=[
        {
            "id": 1,
            "content": "Test memory",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
            "rank": 0.9
        }
    ])
    repo.search_memories_vector = AsyncMock(return_value=[
        {
            "id": 1,
            "content": "Test memory",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
            "distance": 0.1
        }
    ])
    repo.get_recent_memories = AsyncMock(return_value=[])
    
    yield repo


@pytest.fixture
def sample_mcp_request():
    """Sample MCP JSON-RPC request for testing."""
    return {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }


@pytest.fixture
def sample_tool_call_request():
    """Sample tool call request for testing."""
    return {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "read_file",
            "arguments": {
                "file_path": "/test/file.txt"
            }
        },
        "id": 2
    }


@pytest.fixture
def sample_file_content():
    """Sample file content for testing."""
    return {
        "content": "def hello_world():\n    print('Hello, World!')\n",
        "file_path": "/test/file.py",
        "size": 45,
        "encoding": "utf-8"
    }


@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("This is a test file for LocalContextMCP")
    return str(test_file)


@pytest.fixture
def temp_test_dir(tmp_path):
    """Create a temporary test directory with some files."""
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()
    
    # Create some test files
    (test_dir / "main.py").write_text("print('Hello from main')")
    (test_dir / "utils.py").write_text("def utility_function(): pass")
    (test_dir / "README.md").write_text("# Test Project")
    
    # Create subdirectory
    sub_dir = test_dir / "subdir"
    sub_dir.mkdir()
    (sub_dir / "helper.py").write_text("def helper(): return True")
    
    return str(test_dir)