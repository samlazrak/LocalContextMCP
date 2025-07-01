"""Code intelligence tools."""

from typing import Any, Dict, List, Optional
import structlog

from .registry import BaseTool, ToolParameter

logger = structlog.get_logger(__name__)


class CodeCompletionTool(BaseTool):
    """Tool for code completion using LLM."""
    
    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
    
    @property
    def name(self) -> str:
        return "code_completion"
    
    @property
    def description(self) -> str:
        return "Get code completions based on context"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code_context",
                type="string",
                description="Code context for completion",
                required=True
            ),
            ToolParameter(
                name="language",
                type="string",
                description="Programming language",
                required=False,
                default="python"
            ),
            ToolParameter(
                name="max_completions",
                type="integer",
                description="Maximum number of completions to return",
                required=False,
                default=5
            )
        ]
    
    async def execute(
        self,
        code_context: str,
        language: str = "python",
        max_completions: int = 5
    ) -> Dict[str, Any]:
        """Generate code completions."""
        try:
            prompt = f"""
            Generate {max_completions} code completions for the following {language} code context.
            Return only the completion suggestions, each on a new line.
            
            Code context:
            {code_context}
            
            Completions:
            """
            
            response = await self.llm_manager.chat_completion(
                prompt=prompt,
                provider="lmstudio",
                max_tokens=1000,
                temperature=0.2
            )
            
            # Parse completions from response
            completions = [
                line.strip() 
                for line in response.content.split('\n') 
                if line.strip()
            ][:max_completions]
            
            return {
                "completions": completions,
                "language": language,
                "context_length": len(code_context),
                "model": response.model,
                "provider": response.provider
            }
            
        except Exception as e:
            logger.error(f"Code completion failed", error=str(e))
            return {"error": f"Code completion failed: {str(e)}"}


class ProjectAnalysisTool(BaseTool):
    """Tool for basic project analysis."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    @property
    def name(self) -> str:
        return "project_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze a project directory structure"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="project_path",
                type="string",
                description="Path to project directory",
                required=True
            )
        ]
    
    async def execute(self, project_path: str) -> Dict[str, Any]:
        """Analyze project structure."""
        try:
            from pathlib import Path
            
            path = Path(project_path)
            if not path.exists() or not path.is_dir():
                return {"error": f"Invalid project path: {project_path}"}
            
            # Basic analysis
            file_count = 0
            language_stats = {}
            total_size = 0
            
            for item in path.rglob('*'):
                if item.is_file():
                    file_count += 1
                    total_size += item.stat().st_size
                    
                    # Count by extension
                    ext = item.suffix.lower()
                    if ext:
                        language_stats[ext] = language_stats.get(ext, 0) + 1
            
            return {
                "project_path": str(path),
                "file_count": file_count,
                "total_size_bytes": total_size,
                "language_distribution": language_stats,
                "analysis_timestamp": __import__('time').time()
            }
            
        except Exception as e:
            logger.error(f"Project analysis failed", error=str(e))
            return {"error": f"Project analysis failed: {str(e)}"}