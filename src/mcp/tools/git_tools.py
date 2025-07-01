"""Git operation tools."""

import subprocess
from typing import Any, Dict, List
import structlog

from .registry import BaseTool, ToolParameter

logger = structlog.get_logger(__name__)


class GitStatusTool(BaseTool):
    """Tool for getting git status."""
    
    @property
    def name(self) -> str:
        return "git_status"
    
    @property
    def description(self) -> str:
        return "Get the status of a git repository"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="repository_path",
                type="string",
                description="Path to git repository",
                required=False,
                default="."
            )
        ]
    
    async def execute(self, repository_path: str = ".") -> Dict[str, Any]:
        """Get git status."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repository_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {"error": f"Git command failed: {result.stderr}"}
            
            # Parse status output
            changes = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    status = line[:2]
                    filename = line[3:]
                    changes.append({"status": status, "file": filename})
            
            return {
                "repository_path": repository_path,
                "changes": changes,
                "has_changes": len(changes) > 0
            }
            
        except Exception as e:
            logger.error(f"Git status failed", error=str(e))
            return {"error": f"Git status failed: {str(e)}"}


class GitCommitTool(BaseTool):
    """Tool for creating git commits."""
    
    @property
    def name(self) -> str:
        return "git_commit"
    
    @property
    def description(self) -> str:
        return "Create a git commit"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="message",
                type="string",
                description="Commit message",
                required=True
            ),
            ToolParameter(
                name="repository_path",
                type="string",
                description="Path to git repository",
                required=False,
                default="."
            ),
            ToolParameter(
                name="add_all",
                type="boolean",
                description="Add all changes before committing",
                required=False,
                default=False
            )
        ]
    
    async def execute(
        self,
        message: str,
        repository_path: str = ".",
        add_all: bool = False
    ) -> Dict[str, Any]:
        """Create a git commit."""
        try:
            commands = []
            
            # Add all changes if requested
            if add_all:
                commands.append(["git", "add", "."])
            
            # Create commit
            commands.append(["git", "commit", "-m", message])
            
            results = []
            for cmd in commands:
                result = subprocess.run(
                    cmd,
                    cwd=repository_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                results.append({
                    "command": " ".join(cmd),
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                })
                
                if result.returncode != 0:
                    return {
                        "error": f"Command failed: {' '.join(cmd)}",
                        "details": results
                    }
            
            return {
                "repository_path": repository_path,
                "message": message,
                "add_all": add_all,
                "success": True,
                "command_results": results
            }
            
        except Exception as e:
            logger.error(f"Git commit failed", error=str(e))
            return {"error": f"Git commit failed: {str(e)}"}