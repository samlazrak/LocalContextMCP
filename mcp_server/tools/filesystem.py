"""
Filesystem tools for MCP Server.
Provides secure file operations with proper path validation and access control.
"""

import os
import stat
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiofiles

from .base import MCPTool, ToolParameter, ToolResult
from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FileSystemTool(MCPTool):
    """Base class for filesystem tools with security checks."""
    
    def __init__(self):
        super().__init__()
        self.config = get_config().tools
        self.allowed_paths = self.config.fs_allowed_paths
        self.max_file_size = self.config.fs_max_file_size
    
    def _validate_path(self, file_path: str) -> Path:
        """
        Validate and normalize file path for security.
        
        Args:
            file_path: File path to validate
            
        Returns:
            Normalized Path object
            
        Raises:
            ValueError: If path is invalid or not allowed
        """
        try:
            # Normalize the path
            path = Path(file_path).resolve()
            
            # Check if path is within allowed directories
            allowed = False
            for allowed_path in self.allowed_paths:
                allowed_root = Path(allowed_path).resolve()
                try:
                    path.relative_to(allowed_root)
                    allowed = True
                    break
                except ValueError:
                    continue
            
            if not allowed:
                raise ValueError(
                    f"Path '{file_path}' is not within allowed directories: {self.allowed_paths}"
                )
            
            return path
            
        except Exception as e:
            raise ValueError(f"Invalid path '{file_path}': {e}")
    
    def _get_file_info(self, path: Path) -> Dict[str, Any]:
        """Get file information."""
        try:
            stat_info = path.stat()
            
            return {
                "name": path.name,
                "path": str(path),
                "size": stat_info.st_size,
                "is_file": path.is_file(),
                "is_directory": path.is_dir(),
                "is_symlink": path.is_symlink(),
                "permissions": oct(stat_info.st_mode)[-3:],
                "created": stat_info.st_ctime,
                "modified": stat_info.st_mtime,
                "accessed": stat_info.st_atime
            }
        except Exception as e:
            return {"error": str(e)}


class ReadFileTool(FileSystemTool):
    """Tool for reading file contents."""
    
    @property
    def description(self) -> str:
        return "Read the contents of a file"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="Path to the file to read",
                required=True
            ),
            ToolParameter(
                name="encoding",
                type="string",
                description="File encoding (default: utf-8)",
                default="utf-8",
                required=False
            ),
            ToolParameter(
                name="max_size",
                type="integer",
                description="Maximum file size to read in bytes",
                default=None,
                required=False
            )
        ]
    
    async def execute(self, file_path: str, encoding: str = "utf-8", max_size: Optional[int] = None) -> ToolResult:
        """Read file contents."""
        try:
            path = self._validate_path(file_path)
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    error_message=f"File does not exist: {file_path}"
                )
            
            if not path.is_file():
                return ToolResult(
                    success=False,
                    error_message=f"Path is not a file: {file_path}"
                )
            
            # Check file size
            file_size = path.stat().st_size
            size_limit = max_size or self.max_file_size
            
            if file_size > size_limit:
                return ToolResult(
                    success=False,
                    error_message=f"File too large: {file_size} bytes (limit: {size_limit})"
                )
            
            # Read file contents
            async with aiofiles.open(path, 'r', encoding=encoding) as f:
                content = await f.read()
            
            return ToolResult(
                success=True,
                data={
                    "content": content,
                    "file_info": self._get_file_info(path),
                    "encoding": encoding
                }
            )
            
        except UnicodeDecodeError as e:
            return ToolResult(
                success=False,
                error_message=f"Failed to decode file with encoding '{encoding}': {e}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Failed to read file: {e}"
            )


class WriteFileTool(FileSystemTool):
    """Tool for writing file contents."""
    
    @property
    def description(self) -> str:
        return "Write content to a file"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="Path to the file to write",
                required=True
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Content to write to the file",
                required=True
            ),
            ToolParameter(
                name="encoding",
                type="string",
                description="File encoding (default: utf-8)",
                default="utf-8",
                required=False
            ),
            ToolParameter(
                name="create_dirs",
                type="boolean",
                description="Create parent directories if they don't exist",
                default=False,
                required=False
            )
        ]
    
    async def execute(
        self, 
        file_path: str, 
        content: str, 
        encoding: str = "utf-8",
        create_dirs: bool = False
    ) -> ToolResult:
        """Write content to file."""
        try:
            path = self._validate_path(file_path)
            
            # Create parent directories if requested
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if parent directory exists
            if not path.parent.exists():
                return ToolResult(
                    success=False,
                    error_message=f"Parent directory does not exist: {path.parent}"
                )
            
            # Check content size
            content_size = len(content.encode(encoding))
            if content_size > self.max_file_size:
                return ToolResult(
                    success=False,
                    error_message=f"Content too large: {content_size} bytes (limit: {self.max_file_size})"
                )
            
            # Write file
            async with aiofiles.open(path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            return ToolResult(
                success=True,
                data={
                    "file_info": self._get_file_info(path),
                    "bytes_written": content_size,
                    "encoding": encoding
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Failed to write file: {e}"
            )


class ListDirectoryTool(FileSystemTool):
    """Tool for listing directory contents."""
    
    @property
    def description(self) -> str:
        return "List the contents of a directory"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="directory_path",
                type="string",
                description="Path to the directory to list",
                required=True
            ),
            ToolParameter(
                name="include_hidden",
                type="boolean",
                description="Include hidden files and directories",
                default=False,
                required=False
            ),
            ToolParameter(
                name="recursive",
                type="boolean",
                description="List contents recursively",
                default=False,
                required=False
            ),
            ToolParameter(
                name="max_depth",
                type="integer",
                description="Maximum recursion depth",
                default=3,
                required=False
            )
        ]
    
    async def execute(
        self, 
        directory_path: str, 
        include_hidden: bool = False,
        recursive: bool = False,
        max_depth: int = 3
    ) -> ToolResult:
        """List directory contents."""
        try:
            path = self._validate_path(directory_path)
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    error_message=f"Directory does not exist: {directory_path}"
                )
            
            if not path.is_dir():
                return ToolResult(
                    success=False,
                    error_message=f"Path is not a directory: {directory_path}"
                )
            
            # List directory contents
            items = []
            
            if recursive:
                items = self._list_recursive(path, include_hidden, max_depth, 0)
            else:
                items = self._list_directory(path, include_hidden)
            
            return ToolResult(
                success=True,
                data={
                    "directory": str(path),
                    "items": items,
                    "total_items": len(items),
                    "recursive": recursive,
                    "include_hidden": include_hidden
                }
            )
            
        except PermissionError:
            return ToolResult(
                success=False,
                error_message=f"Permission denied accessing directory: {directory_path}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Failed to list directory: {e}"
            )
    
    def _list_directory(self, path: Path, include_hidden: bool) -> List[Dict[str, Any]]:
        """List single directory contents."""
        items = []
        
        for item in path.iterdir():
            # Skip hidden files if not requested
            if not include_hidden and item.name.startswith('.'):
                continue
            
            items.append(self._get_file_info(item))
        
        return sorted(items, key=lambda x: (not x.get('is_directory', False), x.get('name', '')))
    
    def _list_recursive(
        self, 
        path: Path, 
        include_hidden: bool, 
        max_depth: int, 
        current_depth: int
    ) -> List[Dict[str, Any]]:
        """List directory contents recursively."""
        items = []
        
        if current_depth >= max_depth:
            return items
        
        for item in path.iterdir():
            # Skip hidden files if not requested
            if not include_hidden and item.name.startswith('.'):
                continue
            
            file_info = self._get_file_info(item)
            file_info['depth'] = current_depth
            items.append(file_info)
            
            # Recurse into subdirectories
            if item.is_dir() and current_depth < max_depth:
                try:
                    subitems = self._list_recursive(item, include_hidden, max_depth, current_depth + 1)
                    items.extend(subitems)
                except PermissionError:
                    # Skip directories we can't access
                    pass
        
        return items


class CreateDirectoryTool(FileSystemTool):
    """Tool for creating directories."""
    
    @property
    def description(self) -> str:
        return "Create a new directory"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="directory_path",
                type="string",
                description="Path of the directory to create",
                required=True
            ),
            ToolParameter(
                name="parents",
                type="boolean",
                description="Create parent directories if they don't exist",
                default=True,
                required=False
            )
        ]
    
    async def execute(self, directory_path: str, parents: bool = True) -> ToolResult:
        """Create directory."""
        try:
            path = self._validate_path(directory_path)
            
            if path.exists():
                if path.is_dir():
                    return ToolResult(
                        success=True,
                        data={
                            "message": "Directory already exists",
                            "directory_info": self._get_file_info(path)
                        }
                    )
                else:
                    return ToolResult(
                        success=False,
                        error_message=f"Path exists but is not a directory: {directory_path}"
                    )
            
            # Create directory
            path.mkdir(parents=parents, exist_ok=True)
            
            return ToolResult(
                success=True,
                data={
                    "message": "Directory created successfully",
                    "directory_info": self._get_file_info(path)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Failed to create directory: {e}"
            )


class DeleteFileTool(FileSystemTool):
    """Tool for deleting files and directories."""
    
    @property
    def description(self) -> str:
        return "Delete a file or directory"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="Path to the file or directory to delete",
                required=True
            ),
            ToolParameter(
                name="recursive",
                type="boolean",
                description="Delete directories and their contents recursively",
                default=False,
                required=False
            )
        ]
    
    async def execute(self, file_path: str, recursive: bool = False) -> ToolResult:
        """Delete file or directory."""
        try:
            path = self._validate_path(file_path)
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    error_message=f"Path does not exist: {file_path}"
                )
            
            # Store info before deletion
            file_info = self._get_file_info(path)
            
            if path.is_file() or path.is_symlink():
                path.unlink()
                action = "File deleted"
            elif path.is_dir():
                if recursive:
                    import shutil
                    shutil.rmtree(path)
                    action = "Directory deleted recursively"
                else:
                    try:
                        path.rmdir()
                        action = "Empty directory deleted"
                    except OSError:
                        return ToolResult(
                            success=False,
                            error_message="Directory is not empty. Use recursive=true to delete non-empty directories"
                        )
            else:
                return ToolResult(
                    success=False,
                    error_message=f"Unknown file type: {file_path}"
                )
            
            return ToolResult(
                success=True,
                data={
                    "message": action,
                    "deleted_item": file_info
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Failed to delete: {e}"
            )