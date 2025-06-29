#!/usr/bin/env python3
"""
Extensible Language Support Architecture
Provides a plugin-based system for adding new programming language support
"""

import ast
import re
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Type
from dataclasses import dataclass
import importlib
import inspect

logger = logging.getLogger(__name__)

@dataclass
class LanguageInfo:
    """Information about a supported language"""
    name: str
    extensions: List[str]
    parser_class: str
    features: Dict[str, bool]  # completion, search, diagnostics, etc.
    description: str = ""
    version: str = "1.0.0"

class LanguageParserBase(ABC):
    """Base class for all language parsers"""
    
    def __init__(self, language_name: str):
        self.language_name = language_name
        self.features = {
            'symbols': True,
            'dependencies': True,
            'context': True,
            'completion': True,
            'diagnostics': False,
            'formatting': False
        }
    
    @abstractmethod
    def extract_symbols(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract symbols (functions, classes, variables) from code"""
        pass
    
    @abstractmethod
    def extract_dependencies(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract imports/dependencies from code"""
        pass
    
    def get_context_at_position(self, code: str, line: int, column: int) -> Dict[str, Any]:
        """Get context information at specific position"""
        lines = code.split('\n')
        if line > len(lines):
            return {"error": "Line number out of range"}
        
        current_line = lines[line - 1] if line > 0 else ""
        start_line = max(0, line - 5)
        end_line = min(len(lines), line + 5)
        context_lines = lines[start_line:end_line]
        
        return {
            "current_line": current_line,
            "context_lines": context_lines,
            "line_number": line,
            "column_number": column,
            "scope": self._find_scope(code, line)
        }
    
    def get_completions(self, code: str, line: int, column: int) -> List[Dict[str, Any]]:
        """Get completion suggestions"""
        # Default implementation - extract all symbols as completions
        symbols = self.extract_symbols(code, "")
        completions = []
        
        for symbol in symbols:
            completions.append({
                "text": symbol.get("name", ""),
                "kind": symbol.get("type", "unknown"),
                "detail": symbol.get("signature", ""),
                "insertText": symbol.get("name", "")
            })
        
        return completions
    
    def validate_syntax(self, code: str) -> Dict[str, Any]:
        """Validate code syntax"""
        return {"valid": True, "errors": []}
    
    def format_code(self, code: str) -> str:
        """Format code (if supported)"""
        return code
    
    def _find_scope(self, code: str, line: int) -> Dict[str, Any]:
        """Find current scope at line (basic implementation)"""
        return {"type": "global", "name": None}
    
    def get_language_info(self) -> LanguageInfo:
        """Get information about this language parser"""
        return LanguageInfo(
            name=self.language_name,
            extensions=self.get_file_extensions(),
            parser_class=self.__class__.__name__,
            features=self.features,
            description=f"Parser for {self.language_name}"
        )
    
    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """Get list of file extensions this parser supports"""
        pass

class PythonLanguageParser(LanguageParserBase):
    """Enhanced Python language parser with full AST support"""
    
    def __init__(self):
        super().__init__("python")
        self.features.update({
            'diagnostics': True,
            'formatting': True  # via black/autopep8
        })
    
    def extract_symbols(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract Python symbols using AST"""
        symbols = []
        
        try:
            tree = ast.parse(code)
            
            class SymbolExtractor(ast.NodeVisitor):
                def __init__(self):
                    self.current_class = None
                    self.scope_stack = ["global"]
                
                def visit_ClassDef(self, node):
                    symbol = {
                        "name": node.name,
                        "type": "class",
                        "line_start": node.lineno,
                        "line_end": getattr(node, 'end_lineno', node.lineno),
                        "signature": f"class {node.name}",
                        "docstring": ast.get_docstring(node),
                        "scope": self.scope_stack[-1]
                    }
                    symbols.append(symbol)
                    
                    old_class = self.current_class
                    self.current_class = node.name
                    self.scope_stack.append("class")
                    self.generic_visit(node)
                    self.scope_stack.pop()
                    self.current_class = old_class
                
                def visit_FunctionDef(self, node):
                    symbol_type = "method" if self.current_class else "function"
                    args = [arg.arg for arg in node.args.args]
                    signature = f"def {node.name}({', '.join(args)})"
                    
                    symbol = {
                        "name": node.name,
                        "type": symbol_type,
                        "line_start": node.lineno,
                        "line_end": getattr(node, 'end_lineno', node.lineno),
                        "signature": signature,
                        "docstring": ast.get_docstring(node),
                        "scope": self.scope_stack[-1],
                        "parent": self.current_class
                    }
                    symbols.append(symbol)
                    
                    self.scope_stack.append("function")
                    self.generic_visit(node)
                    self.scope_stack.pop()
            
            extractor = SymbolExtractor()
            extractor.visit(tree)
            
        except SyntaxError as e:
            logger.warning(f"Python syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing Python file {file_path}: {e}")
        
        return symbols
    
    def extract_dependencies(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract Python imports"""
        dependencies = []
        
        try:
            tree = ast.parse(code)
            
            class ImportExtractor(ast.NodeVisitor):
                def visit_Import(self, node):
                    for alias in node.names:
                        dep = {
                            "target": alias.name,
                            "name": alias.asname or alias.name,
                            "type": "import",
                            "line": node.lineno,
                            "relative": False
                        }
                        dependencies.append(dep)
                
                def visit_ImportFrom(self, node):
                    module = node.module or ""
                    for alias in node.names:
                        dep = {
                            "target": module,
                            "name": alias.asname or alias.name,
                            "type": "from_import",
                            "line": node.lineno,
                            "relative": node.level > 0
                        }
                        dependencies.append(dep)
            
            extractor = ImportExtractor()
            extractor.visit(tree)
            
        except Exception as e:
            logger.error(f"Error extracting Python dependencies: {e}")
        
        return dependencies
    
    def validate_syntax(self, code: str) -> Dict[str, Any]:
        """Validate Python syntax"""
        try:
            ast.parse(code)
            return {"valid": True, "errors": []}
        except SyntaxError as e:
            return {
                "valid": False,
                "errors": [{
                    "line": e.lineno,
                    "column": e.offset,
                    "message": str(e),
                    "type": "syntax_error"
                }]
            }
    
    def get_file_extensions(self) -> List[str]:
        return ['.py', '.pyw']

class JavaScriptLanguageParser(LanguageParserBase):
    """JavaScript/TypeScript language parser using regex patterns"""
    
    def __init__(self, language_name="javascript"):
        super().__init__(language_name)
        self.is_typescript = language_name == "typescript"
    
    def extract_symbols(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript symbols"""
        symbols = []
        lines = code.split('\n')
        
        patterns = {
            'function': [
                r'function\s+(\w+)\s*\([^)]*\)',
                r'(\w+)\s*:\s*function\s*\([^)]*\)',
                r'(\w+)\s*=\s*function\s*\([^)]*\)',
                r'(\w+)\s*=\s*\([^)]*\)\s*=>',
                r'async\s+function\s+(\w+)\s*\([^)]*\)'
            ],
            'class': [
                r'class\s+(\w+)',
                r'(\w+)\s*=\s*class'
            ],
            'variable': [
                r'(?:var|let|const)\s+(\w+)',
                r'(\w+)\s*:'  # Object properties
            ],
            'interface': [
                r'interface\s+(\w+)'
            ] if self.is_typescript else [],
            'type': [
                r'type\s+(\w+)\s*='
            ] if self.is_typescript else []
        }
        
        for line_num, line in enumerate(lines, 1):
            for symbol_type, regexes in patterns.items():
                for pattern in regexes:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        symbol = {
                            "name": match.group(1),
                            "type": symbol_type,
                            "line_start": line_num,
                            "line_end": line_num,
                            "signature": match.group(0).strip(),
                            "scope": "global"
                        }
                        symbols.append(symbol)
        
        return symbols
    
    def extract_dependencies(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript imports"""
        dependencies = []
        lines = code.split('\n')
        
        patterns = [
            r'import\s+.*\s+from\s+["\']([^"\']+)["\']',
            r'import\s+["\']([^"\']+)["\']',
            r'require\(["\']([^"\']+)["\']\)',
            r'import\(["\']([^"\']+)["\']\)'
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    import_type = "import" if "import" in line else "require"
                    dep = {
                        "target": match.group(1),
                        "name": match.group(1),
                        "type": import_type,
                        "line": line_num,
                        "relative": match.group(1).startswith('.')
                    }
                    dependencies.append(dep)
        
        return dependencies
    
    def get_file_extensions(self) -> List[str]:
        if self.is_typescript:
            return ['.ts', '.tsx']
        return ['.js', '.jsx']

class LanguageRegistry:
    """Registry for managing language parsers"""
    
    def __init__(self):
        self.parsers: Dict[str, Type[LanguageParserBase]] = {}
        self.extension_map: Dict[str, str] = {}  # extension -> language_name
        self._register_builtin_parsers()
    
    def _register_builtin_parsers(self):
        """Register built-in language parsers"""
        self.register_parser("python", PythonLanguageParser)
        self.register_parser("javascript", JavaScriptLanguageParser)
        
        # TypeScript parser class wrapper
        class TypeScriptParser(JavaScriptLanguageParser):
            def __init__(self):
                super().__init__("typescript")
        
        self.register_parser("typescript", TypeScriptParser)
    
    def register_parser(self, language_name: str, parser_class: Type[LanguageParserBase]):
        """Register a language parser"""
        self.parsers[language_name] = parser_class
        
        # Create instance to get file extensions
        try:
            parser_instance = parser_class()
            extensions = parser_instance.get_file_extensions()
            for ext in extensions:
                self.extension_map[ext.lower()] = language_name
            
            logger.info(f"Registered language parser: {language_name} ({extensions})")
        except Exception as e:
            logger.error(f"Error registering parser for {language_name}: {e}")
    
    def get_parser(self, language_name: str) -> Optional[LanguageParserBase]:
        """Get a parser instance for a language"""
        if language_name in self.parsers:
            try:
                return self.parsers[language_name]()
            except Exception as e:
                logger.error(f"Error creating parser for {language_name}: {e}")
        return None
    
    def get_parser_for_file(self, file_path: str) -> Optional[LanguageParserBase]:
        """Get parser for a file based on its extension"""
        ext = Path(file_path).suffix.lower()
        language_name = self.extension_map.get(ext)
        
        if language_name:
            return self.get_parser(language_name)
        return None
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect language from file extension"""
        ext = Path(file_path).suffix.lower()
        return self.extension_map.get(ext)
    
    def list_supported_languages(self) -> List[LanguageInfo]:
        """List all supported languages"""
        languages = []
        for language_name in self.parsers:
            parser = self.get_parser(language_name)
            if parser:
                languages.append(parser.get_language_info())
        return languages
    
    def get_supported_extensions(self) -> List[str]:
        """Get all supported file extensions"""
        return list(self.extension_map.keys())
    
    def load_plugin(self, plugin_path: str) -> bool:
        """Load a language parser plugin from file"""
        try:
            # Import the plugin module
            spec = importlib.util.spec_from_file_location("plugin", plugin_path)
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)
            
            # Find parser classes in the module
            for name, obj in inspect.getmembers(plugin_module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, LanguageParserBase) and 
                    obj != LanguageParserBase):
                    
                    # Register the parser
                    parser_instance = obj()
                    language_name = parser_instance.language_name
                    self.register_parser(language_name, obj)
                    logger.info(f"Loaded plugin parser: {language_name} from {plugin_path}")
                    return True
            
            logger.warning(f"No valid parser classes found in plugin: {plugin_path}")
            return False
            
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_path}: {e}")
            return False

class ExtensibleCodeIntelligence:
    """Extended code intelligence with pluggable language support"""
    
    def __init__(self):
        self.registry = LanguageRegistry()
        self.symbol_cache = {}
        self.dependency_cache = {}
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a file using appropriate language parser"""
        parser = self.registry.get_parser_for_file(file_path)
        if not parser:
            return {"error": f"No parser available for file: {file_path}"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {"error": f"Could not read file: {e}"}
        
        # Extract symbols and dependencies
        symbols = parser.extract_symbols(code, file_path)
        dependencies = parser.extract_dependencies(code, file_path)
        
        # Cache results
        self.symbol_cache[file_path] = symbols
        self.dependency_cache[file_path] = dependencies
        
        return {
            "file_path": file_path,
            "language": parser.language_name,
            "symbols": symbols,
            "dependencies": dependencies,
            "parser": parser.__class__.__name__
        }
    
    def get_completions(self, file_path: str, line: int, column: int, context: str = "") -> List[Dict[str, Any]]:
        """Get completions using appropriate parser"""
        parser = self.registry.get_parser_for_file(file_path)
        if not parser:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            return parser.get_completions(code, line, column)
        except Exception as e:
            logger.error(f"Error getting completions for {file_path}: {e}")
            return []
    
    def search_symbols(self, query: str, language_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search symbols across all cached files"""
        results = []
        
        for file_path, symbols in self.symbol_cache.items():
            # Filter by language if specified
            if language_filter:
                file_language = self.registry.detect_language(file_path)
                if file_language != language_filter:
                    continue
            
            # Search symbols
            for symbol in symbols:
                if query.lower() in symbol.get("name", "").lower():
                    symbol_result = symbol.copy()
                    symbol_result["file_path"] = file_path
                    results.append(symbol_result)
        
        return results
    
    def add_language_support(self, language_name: str, parser_class: Type[LanguageParserBase]):
        """Add support for a new language"""
        self.registry.register_parser(language_name, parser_class)
    
    def load_language_plugin(self, plugin_path: str) -> bool:
        """Load a language plugin from file"""
        return self.registry.load_plugin(plugin_path)
    
    def get_language_info(self) -> Dict[str, Any]:
        """Get information about supported languages"""
        return {
            "supported_languages": [lang.name for lang in self.registry.list_supported_languages()],
            "supported_extensions": self.registry.get_supported_extensions(),
            "language_details": [lang.__dict__ for lang in self.registry.list_supported_languages()]
        }

# Global instance
extensible_code_intelligence = ExtensibleCodeIntelligence() 