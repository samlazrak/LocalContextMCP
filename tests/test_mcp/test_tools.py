"""Tests for MCP tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFileOperationTools:
    """Test file operation tools."""

    @pytest.mark.asyncio
    async def test_read_file_success(self, temp_test_file):
        """Test successful file reading."""
        # Import here to avoid dependency issues during linter check
        try:
            from src.mcp.tools.file_operations import FileReadTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        tool = FileReadTool()
        result = await tool.execute(file_path=temp_test_file)
        
        assert "error" not in result
        assert "content" in result
        assert result["content"] == "This is a test file for LocalContextMCP"
        assert result["encoding"] == "utf-8"

    @pytest.mark.asyncio
    async def test_read_file_not_found(self):
        """Test reading non-existent file."""
        try:
            from src.mcp.tools.file_operations import FileReadTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        tool = FileReadTool()
        result = await tool.execute(file_path="/nonexistent/file.txt")
        
        assert "error" in result
        assert "File not found" in result["error"]

    @pytest.mark.asyncio
    async def test_write_file_success(self, tmp_path):
        """Test successful file writing."""
        try:
            from src.mcp.tools.file_operations import FileWriteTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        tool = FileWriteTool()
        test_file = tmp_path / "new_file.txt"
        test_content = "This is new content"
        
        result = await tool.execute(
            file_path=str(test_file),
            content=test_content
        )
        
        assert "error" not in result
        assert "file_path" in result
        assert test_file.read_text() == test_content

    @pytest.mark.asyncio
    async def test_list_files_success(self, temp_test_dir):
        """Test successful directory listing."""
        try:
            from src.mcp.tools.file_operations import FileListTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        tool = FileListTool()
        result = await tool.execute(directory_path=temp_test_dir)
        
        assert "error" not in result
        assert "files" in result
        assert "directories" in result
        assert result["total_files"] >= 3  # main.py, utils.py, README.md


class TestMemoryTools:
    """Test memory tools."""

    @pytest.mark.asyncio
    async def test_store_memory_success(self, mock_database, mock_llm_manager):
        """Test successful memory storage."""
        try:
            from src.mcp.tools.memory_tools import StoreMemoryTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        # Mock the memory repository
        with patch('src.mcp.tools.memory_tools.MemoryRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.store_memory = AsyncMock(return_value=123)
            mock_repo_class.return_value = mock_repo
            
            tool = StoreMemoryTool(mock_database, mock_llm_manager)
            result = await tool.execute(
                session_id="test_session",
                content="Test memory content"
            )
            
            assert "error" not in result
            assert result["memory_id"] == 123
            assert result["session_id"] == "test_session"
            assert result["content_length"] == len("Test memory content")

    @pytest.mark.asyncio
    async def test_search_memory_success(self, mock_database, mock_llm_manager):
        """Test successful memory search."""
        try:
            from src.mcp.tools.memory_tools import SearchMemoryTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        # Mock the memory repository
        with patch('src.mcp.tools.memory_tools.MemoryRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.search_memories_text = AsyncMock(return_value=[
                {
                    "id": 1,
                    "content": "Found memory",
                    "rank": 0.9
                }
            ])
            mock_repo_class.return_value = mock_repo
            
            tool = SearchMemoryTool(mock_database, mock_llm_manager)
            result = await tool.execute(
                session_id="test_session",
                query="test query"
            )
            
            assert "error" not in result
            assert "results" in result
            assert len(result["results"]) == 1
            assert result["results"][0]["content"] == "Found memory"


class TestCodeTools:
    """Test code intelligence tools."""

    @pytest.mark.asyncio
    async def test_code_completion_success(self, mock_llm_manager):
        """Test successful code completion."""
        try:
            from src.mcp.tools.code_tools import CodeCompletionTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        tool = CodeCompletionTool(mock_llm_manager)
        result = await tool.execute(
            code_context="def hello",
            language="python"
        )
        
        assert "error" not in result
        assert "completions" in result
        assert result["language"] == "python"
        assert "model" in result

    @pytest.mark.asyncio
    async def test_project_analysis_success(self, mock_database, temp_test_dir):
        """Test successful project analysis."""
        try:
            from src.mcp.tools.code_tools import ProjectAnalysisTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        tool = ProjectAnalysisTool(mock_database)
        result = await tool.execute(project_path=temp_test_dir)
        
        assert "error" not in result
        assert "project_path" in result
        assert "file_count" in result
        assert result["file_count"] >= 3
        assert "language_distribution" in result
        assert ".py" in result["language_distribution"]


class TestGitTools:
    """Test Git operation tools."""

    @pytest.mark.asyncio
    async def test_git_status_success(self):
        """Test successful git status."""
        try:
            from src.mcp.tools.git_tools import GitStatusTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        tool = GitStatusTool()
        
        # Mock subprocess.run
        with patch('src.mcp.tools.git_tools.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="M  test_file.py\n",
                stderr=""
            )
            
            result = await tool.execute(repository_path=".")
            
            assert "error" not in result
            assert "changes" in result
            assert len(result["changes"]) == 1
            assert result["changes"][0]["file"] == "test_file.py"

    @pytest.mark.asyncio
    async def test_git_commit_success(self):
        """Test successful git commit."""
        try:
            from src.mcp.tools.git_tools import GitCommitTool
        except ImportError:
            pytest.skip("Dependencies not available")
        
        tool = GitCommitTool()
        
        # Mock subprocess.run
        with patch('src.mcp.tools.git_tools.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[main abc123] Test commit\n",
                stderr=""
            )
            
            result = await tool.execute(
                message="Test commit",
                repository_path="."
            )
            
            assert "error" not in result
            assert result["success"] is True
            assert result["message"] == "Test commit"