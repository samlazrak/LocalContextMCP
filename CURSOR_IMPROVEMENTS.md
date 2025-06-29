# MCP Server Improvements for Cursor-like IDE Experience

## Overview
Transform your MCP server into a powerful distributed IDE backend that rivals Cursor, with your Mac handling data/RAG and desktop handling LLM compute.

## Core Architecture Improvements

### 1. **Code Intelligence Engine**
```python
# Add to new file: code_intelligence.py
import tree_sitter
from tree_sitter import Language, Parser
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional

class CodeIntelligence:
    def __init__(self):
        self.parsers = {
            'python': Language.build_library('build/py.so', ['tree-sitter-python']),
            'javascript': Language.build_library('build/js.so', ['tree-sitter-javascript']),
            'typescript': Language.build_library('build/ts.so', ['tree-sitter-typescript'])
        }
    
    def extract_symbols(self, code: str, language: str) -> List[Dict]:
        """Extract functions, classes, variables from code"""
        pass
    
    def get_call_graph(self, project_path: str) -> Dict:
        """Build call graph for entire project"""
        pass
    
    def analyze_dependencies(self, file_path: str) -> List[str]:
        """Extract import/require dependencies"""
        pass
```

### 2. **Enhanced Context Management**
```python
# Add to new file: semantic_context.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple

class SemanticContextManager:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def chunk_code_semantically(self, code: str, language: str) -> List[Dict]:
        """Chunk code by semantic units (functions, classes, etc.)"""
        pass
    
    def rank_context_relevance(self, query: str, contexts: List[str]) -> List[Tuple[str, float]]:
        """Rank code contexts by relevance to query"""
        pass
    
    def build_hierarchical_context(self, file_path: str) -> Dict:
        """Build file -> class -> method -> statement hierarchy"""
        pass
```

### 3. **Real-time File System Integration**
```python
# Add to new file: file_watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
from typing import Set, Callable

class CodeFileWatcher(FileSystemEventHandler):
    def __init__(self, callback: Callable):
        self.callback = callback
        self.watched_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h'}
    
    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path).suffix in self.watched_extensions:
            asyncio.create_task(self.callback(event.src_path, 'modified'))
    
    def on_created(self, event):
        if not event.is_directory and Path(event.src_path).suffix in self.watched_extensions:
            asyncio.create_task(self.callback(event.src_path, 'created'))
```

## Database Schema Enhancements

### New Tables for Code Intelligence
```sql
-- Enhanced schema additions
CREATE TABLE code_symbols (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    file_path TEXT NOT NULL,
    symbol_name TEXT NOT NULL,
    symbol_type TEXT NOT NULL, -- function, class, variable, etc.
    line_start INTEGER,
    line_end INTEGER,
    column_start INTEGER,
    column_end INTEGER,
    signature TEXT,
    docstring TEXT,
    embedding VECTOR(384),
    parent_symbol_id INTEGER REFERENCES code_symbols(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE file_dependencies (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    source_file TEXT NOT NULL,
    target_file TEXT NOT NULL,
    import_type TEXT, -- import, require, include
    import_name TEXT,
    line_number INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    language TEXT,
    framework TEXT,
    last_indexed TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE code_completions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    context_hash TEXT NOT NULL,
    completion TEXT NOT NULL,
    score FLOAT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE diagnostics (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    file_path TEXT NOT NULL,
    line_number INTEGER,
    column_number INTEGER,
    severity TEXT, -- error, warning, info
    message TEXT,
    source TEXT, -- linter, compiler, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_code_symbols_project_file ON code_symbols(project_id, file_path);
CREATE INDEX idx_code_symbols_name ON code_symbols(symbol_name);
CREATE INDEX idx_file_dependencies_source ON file_dependencies(source_file);
CREATE INDEX idx_diagnostics_file ON diagnostics(project_id, file_path);
```

## Enhanced MCP Tools

### 1. **Advanced Code Search Tool**
```python
@method
def code_search(query: str, project_id: int = None, file_types: List[str] = None):
    """Semantic code search across projects"""
    try:
        # Combine keyword search with semantic similarity
        results = semantic_search_code(query, project_id, file_types)
        return Success(results)
    except Exception as e:
        return Error(f"Code search error: {e}")

@method
def symbol_lookup(symbol_name: str, project_id: int = None):
    """Find symbol definitions and references"""
    try:
        definitions = find_symbol_definitions(symbol_name, project_id)
        references = find_symbol_references(symbol_name, project_id)
        return Success({"definitions": definitions, "references": references})
    except Exception as e:
        return Error(f"Symbol lookup error: {e}")
```

### 2. **Code Completion Tool**
```python
@method
def code_complete(file_path: str, line: int, column: int, context: str):
    """Generate code completions based on context"""
    try:
        # Get relevant context from database
        context_chunks = get_relevant_context(file_path, line, column)
        
        # Call desktop LLM for completion
        completion = call_remote_llm({
            "context": context_chunks,
            "current_line": context,
            "file_path": file_path,
            "task": "code_completion"
        })
        
        # Cache the completion
        cache_completion(file_path, context, completion)
        
        return Success(completion)
    except Exception as e:
        return Error(f"Code completion error: {e}")
```

### 3. **Project Analysis Tool**
```python
@method
def analyze_project(project_path: str):
    """Comprehensive project analysis"""
    try:
        analysis = {
            "structure": analyze_project_structure(project_path),
            "dependencies": extract_all_dependencies(project_path),
            "complexity": calculate_complexity_metrics(project_path),
            "test_coverage": analyze_test_coverage(project_path),
            "code_quality": run_code_quality_checks(project_path)
        }
        return Success(analysis)
    except Exception as e:
        return Error(f"Project analysis error: {e}")
```

## Network Architecture Improvements

### 1. **Efficient RPC Communication**
```python
# Add to new file: network.py
import asyncio
import aiohttp
from typing import Dict, Any
import json

class DesktopLLMClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
    
    async def initialize(self):
        self.session = aiohttp.ClientSession()
    
    async def call_llm(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Async call to desktop LLM with proper error handling"""
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                return await response.json()
        except asyncio.TimeoutError:
            return {"error": "Desktop LLM timeout"}
        except Exception as e:
            return {"error": f"Desktop LLM error: {e}"}
    
    async def stream_completion(self, payload: Dict[str, Any]):
        """Stream completion from desktop LLM"""
        async with self.session.post(
            f"{self.base_url}/v1/chat/completions",
            json={**payload, "stream": True}
        ) as response:
            async for line in response.content:
                if line:
                    yield json.loads(line.decode())
```

### 2. **Caching Strategy**
```python
# Add to new file: cache_manager.py
import redis
import json
from typing import Any, Optional
import hashlib

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def cache_completion(self, context: str, completion: str, ttl: int = 3600):
        """Cache code completions with TTL"""
        key = f"completion:{hashlib.md5(context.encode()).hexdigest()}"
        self.redis_client.setex(key, ttl, json.dumps(completion))
    
    def get_cached_completion(self, context: str) -> Optional[str]:
        """Retrieve cached completion"""
        key = f"completion:{hashlib.md5(context.encode()).hexdigest()}"
        cached = self.redis_client.get(key)
        return json.loads(cached) if cached else None
    
    def cache_project_analysis(self, project_path: str, analysis: Dict):
        """Cache project analysis results"""
        key = f"project:{hashlib.md5(project_path.encode()).hexdigest()}"
        self.redis_client.setex(key, 1800, json.dumps(analysis))  # 30 min TTL
```

## Language Server Protocol Integration

### 1. **LSP Client Integration**
```python
# Add to new file: lsp_integration.py
from pylsp import lsp
import asyncio
from typing import List, Dict

class LSPManager:
    def __init__(self):
        self.language_servers = {}
    
    async def start_language_server(self, language: str, project_path: str):
        """Start LSP server for specific language"""
        if language == 'python':
            server = await self.start_pylsp(project_path)
            self.language_servers[f"{language}:{project_path}"] = server
    
    async def get_diagnostics(self, file_path: str) -> List[Dict]:
        """Get diagnostics from appropriate LSP server"""
        pass
    
    async def get_hover_info(self, file_path: str, line: int, character: int) -> Dict:
        """Get hover information from LSP"""
        pass
    
    async def get_definitions(self, file_path: str, line: int, character: int) -> List[Dict]:
        """Get symbol definitions"""
        pass
```

## Enhanced RAG Implementation

### 1. **Multi-level Context Retrieval**
```python
# Add to enhanced_rag.py
class EnhancedRAG:
    def __init__(self):
        self.context_levels = ['statement', 'function', 'class', 'file', 'project']
    
    def get_contextual_embeddings(self, query: str, file_path: str) -> Dict:
        """Get embeddings at multiple granularity levels"""
        contexts = {}
        for level in self.context_levels:
            contexts[level] = self.retrieve_context_at_level(query, file_path, level)
        return contexts
    
    def rank_and_combine_contexts(self, contexts: Dict, max_tokens: int = 4000) -> str:
        """Intelligently combine contexts within token limit"""
        pass
    
    def adaptive_context_selection(self, query_type: str, contexts: Dict) -> str:
        """Select context based on query type (completion, explanation, debugging)"""
        pass
```

## Implementation Priority

### Phase 1: Core Infrastructure (Week 1-2)
1. Fix current linter errors
2. Implement tree-sitter integration
3. Set up enhanced database schema
4. Add file watching system

### Phase 2: Code Intelligence (Week 3-4)
1. Symbol extraction and indexing
2. Dependency analysis
3. Call graph generation
4. Semantic code search

### Phase 3: Network & Caching (Week 5-6)
1. Async RPC communication with desktop
2. Redis caching implementation
3. Connection pooling and error handling
4. Load balancing for multiple desktop instances

### Phase 4: Advanced Features (Week 7-8)
1. LSP integration
2. Code completion with ranking
3. Real-time diagnostics
4. Project-wide refactoring support

### Phase 5: IDE Features (Week 9-10)
1. Syntax highlighting service
2. Code formatting integration
3. Git integration enhancements
4. Workspace management

## Performance Optimizations

### 1. **Incremental Indexing**
- Only re-index changed files
- Use file modification timestamps
- Implement differential updates

### 2. **Smart Context Caching**
- Cache frequently accessed code contexts
- Pre-compute embeddings for common patterns
- Use LRU cache for recent completions

### 3. **Asynchronous Processing**
- Background indexing of projects
- Async communication with desktop LLM
- Non-blocking file system operations

## Monitoring and Observability

### 1. **Metrics Collection**
```python
# Add to metrics.py
from prometheus_client import Counter, Histogram, Gauge

completion_requests = Counter('code_completion_requests_total')
completion_latency = Histogram('code_completion_duration_seconds')
active_projects = Gauge('active_projects_count')
```

### 2. **Health Checks**
- Desktop LLM connectivity
- Database performance
- Cache hit rates
- File indexing status

This comprehensive improvement plan will transform your MCP server into a powerful Cursor-like IDE backend that leverages your distributed architecture effectively. 