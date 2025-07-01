"""Memory tools for storing and searching conversation context."""

from typing import Any, Dict, List, Optional
import structlog

from .registry import BaseTool, ToolParameter

logger = structlog.get_logger(__name__)


class StoreMemoryTool(BaseTool):
    """Tool for storing memories."""
    
    def __init__(self, db_manager, llm_manager):
        self.db_manager = db_manager
        self.llm_manager = llm_manager
    
    @property
    def name(self) -> str:
        return "store_memory"
    
    @property
    def description(self) -> str:
        return "Store a memory with optional embedding for semantic search"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="session_id",
                type="string",
                description="Session ID to associate the memory with",
                required=True
            ),
            ToolParameter(
                name="content",
                type="string", 
                description="Memory content to store",
                required=True
            ),
            ToolParameter(
                name="metadata",
                type="object",
                description="Optional metadata as key-value pairs",
                required=False,
                default={}
            )
        ]
    
    async def execute(
        self,
        session_id: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Store a memory."""
        try:
            if metadata is None:
                metadata = {}
            
            # Generate embedding for semantic search
            embedding = None
            try:
                if self.llm_manager:
                    embed_response = await self.llm_manager.embedding(content)
                    embedding = embed_response.embedding
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
            
            # Store in database
            from ...core.database import MemoryRepository
            memory_repo = MemoryRepository(self.db_manager)
            
            memory_id = await memory_repo.store_memory(
                session_id=session_id,
                content=content,
                embedding=embedding,
                metadata=metadata
            )
            
            return {
                "memory_id": memory_id,
                "session_id": session_id,
                "content_length": len(content),
                "has_embedding": embedding is not None,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to store memory", error=str(e))
            return {"error": f"Failed to store memory: {str(e)}"}


class SearchMemoryTool(BaseTool):
    """Tool for searching memories."""
    
    def __init__(self, db_manager, llm_manager):
        self.db_manager = db_manager
        self.llm_manager = llm_manager
    
    @property
    def name(self) -> str:
        return "search_memory"
    
    @property
    def description(self) -> str:
        return "Search memories using text or semantic search"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="session_id",
                type="string",
                description="Session ID to search within",
                required=True
            ),
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of results to return",
                required=False,
                default=10
            ),
            ToolParameter(
                name="use_semantic",
                type="boolean",
                description="Use semantic search if available",
                required=False,
                default=True
            )
        ]
    
    async def execute(
        self,
        session_id: str,
        query: str,
        limit: int = 10,
        use_semantic: bool = True
    ) -> Dict[str, Any]:
        """Search memories."""
        try:
            from ...core.database import MemoryRepository
            memory_repo = MemoryRepository(self.db_manager)
            
            results = []
            search_type = "text"
            
            # Try semantic search first if requested
            if use_semantic and self.llm_manager:
                try:
                    embed_response = await self.llm_manager.embedding(query)
                    semantic_results = await memory_repo.search_memories_vector(
                        session_id=session_id,
                        embedding=embed_response.embedding,
                        limit=limit
                    )
                    if semantic_results:
                        results = semantic_results
                        search_type = "semantic"
                except Exception as e:
                    logger.warning(f"Semantic search failed: {e}")
            
            # Fallback to text search
            if not results:
                results = await memory_repo.search_memories_text(
                    session_id=session_id,
                    query=query,
                    limit=limit
                )
                search_type = "text"
            
            return {
                "results": results,
                "query": query,
                "session_id": session_id,
                "search_type": search_type,
                "count": len(results),
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"Failed to search memories", error=str(e))
            return {"error": f"Failed to search memories: {str(e)}"}