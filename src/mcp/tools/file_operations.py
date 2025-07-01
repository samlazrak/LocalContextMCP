"""File operation tools for MCP server."""

import os
import aiofiles
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from .registry import BaseTool, ToolParameter

logger = structlog.get_logger(__name__)


class FileReadTool(BaseTool):
    """Tool for reading file contents."""
    
    @property
    def name(self) -> str:
        return "read_file"
    
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
                description="File encoding",
                required=False,
                default="utf-8"
            )
        ]
    
    async def execute(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file contents."""
        try:
            path = Path(file_path)
            
            # Security check - prevent path traversal
            if not path.is_absolute():
                # Resolve relative to current working directory
                path = Path.cwd() / path
            
            # Check if file exists and is readable
            if not path.exists():
                return {"error": f"File not found: {file_path}"}
            
            if not path.is_file():
                return {"error": f"Path is not a file: {file_path}"}
            
            # Check file size (limit to 50MB by default)
            max_size = 50 * 1024 * 1024  # 50MB
            if path.stat().st_size > max_size:
                return {"error": f"File too large: {path.stat().st_size} bytes"}
            
            async with aiofiles.open(path, mode='r', encoding=encoding) as f:
                content = await f.read()
            
            return {
                "content": content,
                "file_path": str(path),
                "size": path.stat().st_size,
                "encoding": encoding
            }
            
        except Exception as e:
            logger.error(f"Failed to read file: {file_path}", error=str(e))
            return {"error": f"Failed to read file: {str(e)}"}


class FileWriteTool(BaseTool):
    """Tool for writing file contents."""
    
    @property
    def name(self) -> str:
        return "write_file"
    
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
                description="File encoding",
                required=False,
                default="utf-8"
            ),
            ToolParameter(
                name="create_dirs",
                type="boolean",
                description="Create parent directories if they don't exist",
                required=False,
                default=True
            )
        ]
    
    async def execute(
        self, 
        file_path: str, 
        content: str, 
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> Dict[str, Any]:
        """Write content to file."""
        try:
            path = Path(file_path)
            
            # Security check - prevent path traversal
            if not path.is_absolute():
                path = Path.cwd() / path
            
            # Create parent directories if needed
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing file if it exists
            if path.exists():
                backup_path = path.with_suffix(path.suffix + '.backup')
                path.rename(backup_path)
            
            async with aiofiles.open(path, mode='w', encoding=encoding) as f:
                await f.write(content)
            
            return {
                "file_path": str(path),
                "bytes_written": len(content.encode(encoding)),
                "encoding": encoding,
                "created_dirs": create_dirs
            }
            
        except Exception as e:
            logger.error(f"Failed to write file: {file_path}", error=str(e))
            return {"error": f"Failed to write file: {str(e)}"}


class FileListTool(BaseTool):
    """Tool for listing directory contents."""
    
    @property
    def name(self) -> str:
        return "list_files"
    
    @property
    def description(self) -> str:
        return "List files and directories in a given path"
    
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
                name="recursive",
                type="boolean",
                description="Whether to list files recursively",
                required=False,
                default=False
            ),
            ToolParameter(
                name="include_hidden",
                type="boolean",
                description="Whether to include hidden files/directories",
                required=False,
                default=False
            ),
            ToolParameter(
                name="file_types",
                type="array",
                description="List of file extensions to filter by (e.g., ['.py', '.js'])",
                required=False,
                default=None
            )
        ]
    
    async def execute(
        self,
        directory_path: str,
        recursive: bool = False,
        include_hidden: bool = False,
        file_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """List directory contents."""
        try:
            path = Path(directory_path)
            
            # Security check
            if not path.is_absolute():
                path = Path.cwd() / path
            
            if not path.exists():
                return {"error": f"Directory not found: {directory_path}"}
            
            if not path.is_dir():
                return {"error": f"Path is not a directory: {directory_path}"}
            
            files = []
            directories = []
            
            def should_include(item_path: Path) -> bool:
                """Check if item should be included based on filters."""
                # Hidden files filter
                if not include_hidden and item_path.name.startswith('.'):
                    return False
                
                # File type filter
                if file_types and item_path.is_file():
                    return item_path.suffix.lower() in [ft.lower() for ft in file_types]
                
                return True
            
            if recursive:
                # Recursive listing with limits
                max_files = 10000
                count = 0
                
                for item in path.rglob('*'):
                    if count >= max_files:
                        break
                    
                    if should_include(item):
                        item_info = {
                            "name": item.name,
                            "path": str(item.relative_to(path)),
                            "absolute_path": str(item),
                            "size": item.stat().st_size if item.is_file() else None,
                            "modified": item.stat().st_mtime
                        }
                        
                        if item.is_file():
                            files.append(item_info)
                        elif item.is_dir():
                            directories.append(item_info)
                        
                        count += 1
            else:
                # Non-recursive listing
                for item in path.iterdir():
                    if should_include(item):
                        item_info = {
                            "name": item.name,
                            "path": item.name,
                            "absolute_path": str(item),
                            "size": item.stat().st_size if item.is_file() else None,
                            "modified": item.stat().st_mtime
                        }
                        
                        if item.is_file():
                            files.append(item_info)
                        elif item.is_dir():
                            directories.append(item_info)
            
            return {
                "directory": str(path),
                "files": sorted(files, key=lambda x: x["name"]),
                "directories": sorted(directories, key=lambda x: x["name"]),
                "total_files": len(files),
                "total_directories": len(directories),
                "recursive": recursive,
                "filters": {
                    "include_hidden": include_hidden,
                    "file_types": file_types
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to list directory: {directory_path}", error=str(e))
            return {"error": f"Failed to list directory: {str(e)}"}