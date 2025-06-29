#!/usr/bin/env python3
"""
Code Intelligence Engine for Project-Aware Completions and Search
Provides AST parsing, symbol extraction, and semantic analysis
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import json
import hashlib
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class CodeSymbol:
    """Represents a code symbol (function, class, variable, etc.)"""
    name: str
    symbol_type: str  # function, class, variable, method, property
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    signature: str
    docstring: Optional[str] = None
    parent: Optional[str] = None  # parent class/function
    scope: str = "global"  # global, class, function
    language: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "type": self.symbol_type,
            "file": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "signature": self.signature,
            "docstring": self.docstring,
            "parent": self.parent,
            "scope": self.scope,
            "language": self.language
        }

@dataclass
class FileDependency:
    """Represents a file dependency (import/require)"""
    source_file: str
    target_file: str
    import_name: str
    import_type: str  # import, from_import, require, include
    line_number: int
    is_relative: bool = False

class LanguageParser:
    """Base class for language-specific parsers"""
    
    def __init__(self, language: str):
        self.language = language
        
    def extract_symbols(self, code: str, file_path: str) -> List[CodeSymbol]:
        """Extract symbols from code"""
        raise NotImplementedError
        
    def extract_dependencies(self, code: str, file_path: str) -> List[FileDependency]:
        """Extract dependencies from code"""
        raise NotImplementedError
        
    def get_context_at_position(self, code: str, line: int, column: int) -> Dict[str, Any]:
        """Get context information at specific position"""
        raise NotImplementedError

class PythonParser(LanguageParser):
    """Python-specific AST parser"""
    
    def __init__(self):
        super().__init__("python")
        
    def extract_symbols(self, code: str, file_path: str) -> List[CodeSymbol]:
        """Extract Python symbols using AST"""
        symbols = []
        
        try:
            tree = ast.parse(code)
            
            class SymbolExtractor(ast.NodeVisitor):
                def __init__(self):
                    self.current_class = None
                    self.current_function = None
                    self.scope_stack = ["global"]
                    
                def visit_ClassDef(self, node):
                    symbol = CodeSymbol(
                        name=node.name,
                        symbol_type="class",
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        column_start=node.col_offset,
                        column_end=getattr(node, 'end_col_offset', node.col_offset),
                        signature=f"class {node.name}",
                        docstring=ast.get_docstring(node),
                        parent=self.current_class,
                        scope=self.scope_stack[-1],
                        language="python"
                    )
                    symbols.append(symbol)
                    
                    # Process class body
                    old_class = self.current_class
                    self.current_class = node.name
                    self.scope_stack.append("class")
                    self.generic_visit(node)
                    self.scope_stack.pop()
                    self.current_class = old_class
                    
                def visit_FunctionDef(self, node):
                    symbol_type = "method" if self.current_class else "function"
                    
                    # Build signature
                    args = []
                    for arg in node.args.args:
                        args.append(arg.arg)
                    signature = f"def {node.name}({', '.join(args)})"
                    
                    symbol = CodeSymbol(
                        name=node.name,
                        symbol_type=symbol_type,
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        column_start=node.col_offset,
                        column_end=getattr(node, 'end_col_offset', node.col_offset),
                        signature=signature,
                        docstring=ast.get_docstring(node),
                        parent=self.current_class,
                        scope=self.scope_stack[-1],
                        language="python"
                    )
                    symbols.append(symbol)
                    
                    # Process function body
                    old_function = self.current_function
                    self.current_function = node.name
                    self.scope_stack.append("function")
                    self.generic_visit(node)
                    self.scope_stack.pop()
                    self.current_function = old_function
                    
                def visit_Assign(self, node):
                    # Extract variable assignments
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            symbol = CodeSymbol(
                                name=target.id,
                                symbol_type="variable",
                                file_path=file_path,
                                line_start=node.lineno,
                                line_end=getattr(node, 'end_lineno', node.lineno),
                                column_start=node.col_offset,
                                column_end=getattr(node, 'end_col_offset', node.col_offset),
                                signature=f"{target.id} = ...",
                                parent=self.current_class or self.current_function,
                                scope=self.scope_stack[-1],
                                language="python"
                            )
                            symbols.append(symbol)
                    self.generic_visit(node)
            
            extractor = SymbolExtractor()
            extractor.visit(tree)
            
        except SyntaxError as e:
            logger.warning(f"Syntax error parsing {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            
        return symbols
    
    def extract_dependencies(self, code: str, file_path: str) -> List[FileDependency]:
        """Extract Python imports"""
        dependencies = []
        
        try:
            tree = ast.parse(code)
            
            class ImportExtractor(ast.NodeVisitor):
                def visit_Import(self, node):
                    for alias in node.names:
                        dep = FileDependency(
                            source_file=file_path,
                            target_file=alias.name,
                            import_name=alias.asname or alias.name,
                            import_type="import",
                            line_number=node.lineno,
                            is_relative=False
                        )
                        dependencies.append(dep)
                
                def visit_ImportFrom(self, node):
                    module = node.module or ""
                    for alias in node.names:
                        dep = FileDependency(
                            source_file=file_path,
                            target_file=module,
                            import_name=alias.asname or alias.name,
                            import_type="from_import", 
                            line_number=node.lineno,
                            is_relative=node.level > 0
                        )
                        dependencies.append(dep)
            
            extractor = ImportExtractor()
            extractor.visit(tree)
            
        except Exception as e:
            logger.error(f"Error extracting dependencies from {file_path}: {e}")
            
        return dependencies
        
    def get_context_at_position(self, code: str, line: int, column: int) -> Dict[str, Any]:
        """Get Python context at specific position"""
        try:
            lines = code.split('\n')
            if line > len(lines):
                return {"error": "Line number out of range"}
                
            current_line = lines[line - 1] if line > 0 else ""
            
            # Find current scope
            tree = ast.parse(code)
            current_scope = self._find_scope_at_position(tree, line, column)
            
            # Get surrounding lines for context
            start_line = max(0, line - 5)
            end_line = min(len(lines), line + 5)
            context_lines = lines[start_line:end_line]
            
            return {
                "current_line": current_line,
                "current_scope": current_scope,
                "context_lines": context_lines,
                "line_number": line,
                "column_number": column
            }
            
        except Exception as e:
            logger.error(f"Error getting context at position: {e}")
            return {"error": str(e)}
    
    def _find_scope_at_position(self, tree: ast.AST, line: int, column: int) -> Dict[str, Any]:
        """Find the scope (class/function) at given position"""
        current_scope = {"type": "global", "name": None}
        
        class ScopeFinder(ast.NodeVisitor):
            def __init__(self):
                self.scope = {"type": "global", "name": None}
                
            def visit_ClassDef(self, node):
                if (node.lineno <= line <= getattr(node, 'end_lineno', node.lineno)):
                    self.scope = {"type": "class", "name": node.name}
                self.generic_visit(node)
                
            def visit_FunctionDef(self, node):
                if (node.lineno <= line <= getattr(node, 'end_lineno', node.lineno)):
                    self.scope = {"type": "function", "name": node.name}
                self.generic_visit(node)
        
        finder = ScopeFinder()
        finder.visit(tree)
        return finder.scope

class JavaScriptParser(LanguageParser):
    """JavaScript/TypeScript parser using regex patterns"""
    
    def __init__(self, language="javascript"):
        super().__init__(language)
        
    def extract_symbols(self, code: str, file_path: str) -> List[CodeSymbol]:
        """Extract JavaScript symbols using regex patterns"""
        symbols = []
        lines = code.split('\n')
        
        # Patterns for different symbol types
        patterns = {
            'function': [
                r'function\s+(\w+)\s*\([^)]*\)',
                r'(\w+)\s*:\s*function\s*\([^)]*\)',
                r'(\w+)\s*=\s*function\s*\([^)]*\)',
                r'(\w+)\s*=\s*\([^)]*\)\s*=>'
            ],
            'class': [
                r'class\s+(\w+)',
                r'(\w+)\s*=\s*class'
            ],
            'variable': [
                r'(?:var|let|const)\s+(\w+)',
                r'(\w+)\s*:'  # Object properties
            ]
        }
        
        for line_num, line in enumerate(lines, 1):
            for symbol_type, regexes in patterns.items():
                for pattern in regexes:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        symbol = CodeSymbol(
                            name=match.group(1),
                            symbol_type=symbol_type,
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            column_start=match.start(),
                            column_end=match.end(),
                            signature=match.group(0),
                            language=self.language
                        )
                        symbols.append(symbol)
        
        return symbols
    
    def extract_dependencies(self, code: str, file_path: str) -> List[FileDependency]:
        """Extract JavaScript imports/requires"""
        dependencies = []
        lines = code.split('\n')
        
        patterns = [
            r'import\s+.*\s+from\s+["\']([^"\']+)["\']',
            r'require\(["\']([^"\']+)["\']\)',
            r'import\(["\']([^"\']+)["\']\)'
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    import_type = "import" if "import" in line else "require"
                    dep = FileDependency(
                        source_file=file_path,
                        target_file=match.group(1),
                        import_name=match.group(1),
                        import_type=import_type,
                        line_number=line_num,
                        is_relative=match.group(1).startswith('.')
                    )
                    dependencies.append(dep)
        
        return dependencies
    
    def get_context_at_position(self, code: str, line: int, column: int) -> Dict[str, Any]:
        """Get JavaScript context at position"""
        lines = code.split('\n')
        if line > len(lines):
            return {"error": "Line number out of range"}
            
        current_line = lines[line - 1] if line > 0 else ""
        
        # Simple scope detection
        scope = self._find_js_scope(lines, line)
        
        start_line = max(0, line - 5)
        end_line = min(len(lines), line + 5)
        context_lines = lines[start_line:end_line]
        
        return {
            "current_line": current_line,
            "current_scope": scope,
            "context_lines": context_lines,
            "line_number": line,
            "column_number": column
        }
    
    def _find_js_scope(self, lines: List[str], target_line: int) -> Dict[str, Any]:
        """Find JavaScript scope at line"""
        # Simple scope detection based on function/class keywords
        for i in range(target_line - 1, -1, -1):
            line = lines[i]
            if re.search(r'function\s+(\w+)', line):
                match = re.search(r'function\s+(\w+)', line)
                return {"type": "function", "name": match.group(1)}
            elif re.search(r'class\s+(\w+)', line):
                match = re.search(r'class\s+(\w+)', line)
                return {"type": "class", "name": match.group(1)}
        
        return {"type": "global", "name": None}

class CodeIntelligence:
    """Main code intelligence engine"""
    
    def __init__(self):
        self.parsers = {
            'python': PythonParser(),
            'javascript': JavaScriptParser('javascript'),
            'typescript': JavaScriptParser('typescript')
        }
        self.symbol_cache = {}
        self.dependency_cache = {}
        
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file and extract symbols and dependencies"""
        if not os.path.exists(file_path):
            return {"error": "File not found"}
            
        language = self._detect_language(file_path)
        if language not in self.parsers:
            return {"error": f"Unsupported language: {language}"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {"error": f"Could not read file: {e}"}
        
        parser = self.parsers[language]
        
        # Extract symbols and dependencies
        symbols = parser.extract_symbols(code, file_path)
        dependencies = parser.extract_dependencies(code, file_path)
        
        # Cache results
        file_hash = hashlib.md5(code.encode()).hexdigest()
        self.symbol_cache[file_path] = {
            "symbols": symbols,
            "hash": file_hash,
            "timestamp": os.path.getmtime(file_path)
        }
        self.dependency_cache[file_path] = dependencies
        
        return {
            "file_path": file_path,
            "language": language,
            "symbols": [s.to_dict() for s in symbols],
            "dependencies": [dep.__dict__ for dep in dependencies],
            "symbol_count": len(symbols),
            "dependency_count": len(dependencies)
        }
    
    def analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze entire project structure"""
        if not os.path.exists(project_path):
            return {"error": "Project path not found"}
        
        project_files = []
        all_symbols = []
        all_dependencies = []
        
        # Walk through project files
        for root, dirs, files in os.walk(project_path):
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            
            for file in files:
                if self._is_code_file(file):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_path)
                    
                    # Analyze file
                    analysis = self.analyze_file(file_path)
                    if "error" not in analysis:
                        project_files.append(rel_path)
                        all_symbols.extend(analysis["symbols"])
                        all_dependencies.extend(analysis["dependencies"])
        
        # Build project statistics
        language_stats = defaultdict(int)
        symbol_stats = defaultdict(int)
        
        for symbol in all_symbols:
            language_stats[symbol["language"]] += 1
            symbol_stats[symbol["type"]] += 1
        
        return {
            "project_path": project_path,
            "total_files": len(project_files),
            "files": project_files,
            "total_symbols": len(all_symbols),
            "total_dependencies": len(all_dependencies),
            "language_distribution": dict(language_stats),
            "symbol_distribution": dict(symbol_stats),
            "symbols": all_symbols,
            "dependencies": all_dependencies
        }
    
    def search_symbols(self, query: str, project_path: str = None, symbol_types: List[str] = None) -> List[Dict]:
        """Search for symbols across project"""
        results = []
        
        # Use cached symbols if available
        for file_path, cache_data in self.symbol_cache.items():
            if project_path and not file_path.startswith(project_path):
                continue
                
            for symbol in cache_data["symbols"]:
                symbol_dict = symbol.to_dict()
                
                # Filter by symbol type if specified
                if symbol_types and symbol_dict["type"] not in symbol_types:
                    continue
                
                # Simple text matching (can be enhanced with fuzzy search)
                if query.lower() in symbol_dict["name"].lower():
                    symbol_dict["score"] = self._calculate_match_score(query, symbol_dict["name"])
                    results.append(symbol_dict)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results
    
    def get_completions(self, file_path: str, line: int, column: int, context: str) -> List[Dict]:
        """Get code completions for position"""
        if not os.path.exists(file_path):
            return []
        
        language = self._detect_language(file_path)
        if language not in self.parsers:
            return []
        
        parser = self.parsers[language]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            logger.error(f"Could not read file for completions: {e}")
            return []
        
        # Get context at position
        position_context = parser.get_context_at_position(code, line, column)
        
        # Get symbols from current file and project
        completions = []
        
        # Add symbols from current file
        if file_path in self.symbol_cache:
            for symbol in self.symbol_cache[file_path]["symbols"]:
                symbol_dict = symbol.to_dict()
                completions.append({
                    "text": symbol.name,
                    "kind": symbol.symbol_type,
                    "detail": symbol.signature,
                    "documentation": symbol.docstring,
                    "source": "current_file"
                })
        
        # Add symbols from imported modules
        if file_path in self.dependency_cache:
            for dep in self.dependency_cache[file_path]:
                # This would be enhanced to resolve actual imported symbols
                completions.append({
                    "text": dep.import_name,
                    "kind": "module",
                    "detail": f"from {dep.target_file}",
                    "source": "import"
                })
        
        return completions[:50]  # Limit to top 50 completions
    
    def invalidate_file_cache(self, file_path: str):
        """Invalidate cache for a file"""
        if file_path in self.symbol_cache:
            del self.symbol_cache[file_path]
        if file_path in self.dependency_cache:
            del self.dependency_cache[file_path]
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript'
        }
        return language_map.get(ext, 'unknown')
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a supported code file"""
        supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        return Path(filename).suffix.lower() in supported_extensions
    
    def _calculate_match_score(self, query: str, target: str) -> float:
        """Calculate relevance score for search match"""
        query_lower = query.lower()
        target_lower = target.lower()
        
        # Exact match gets highest score
        if query_lower == target_lower:
            return 1.0
        
        # Prefix match gets high score
        if target_lower.startswith(query_lower):
            return 0.8
        
        # Contains match gets medium score
        if query_lower in target_lower:
            return 0.6
        
        # No match
        return 0.0

# Global instance
code_intelligence = CodeIntelligence() 