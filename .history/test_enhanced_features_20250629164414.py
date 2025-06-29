#!/usr/bin/env python3
"""
Test script for enhanced MCP server features
Demonstrates rich context, real-time updates, and extensible architecture
"""

import asyncio
import json
import requests
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

# Test configuration
MCP_SERVER_URL = "http://localhost:8080/"

def jsonrpc_call(method: str, params: dict = None, id: int = 1) -> dict:
    """Make a JSON-RPC call to the MCP server"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": id
    }
    if params is not None:
        payload["params"] = params
    
    response = requests.post(MCP_SERVER_URL, json=payload)
    return response.json()

def test_language_support():
    """Test extensible language support"""
    print("🔍 Testing Language Support...")
    
    # Get language support info
    result = jsonrpc_call("tools/call", {
        "tool": "get_language_support"
    })
    
    if "result" in result:
        lang_info = result["result"]
        print(f"✅ Supported languages: {lang_info.get('extensible_support', {}).get('supported_languages', [])}")
        print(f"✅ Supported extensions: {lang_info.get('extensible_support', {}).get('supported_extensions', [])}")
        print(f"✅ Total languages: {lang_info.get('total_supported', 0)}")
    else:
        print(f"❌ Language support test failed: {result}")

def test_project_watching():
    """Test real-time file watching"""
    print("\n📁 Testing Project Watching...")
    
    # Create a temporary project directory
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = temp_dir
        
        # Add project to watching
        result = jsonrpc_call("tools/call", {
            "tool": "add_project_watch",
            "params": {
                "project_path": project_path,
                "project_name": "test_project"
            }
        })
        
        if "result" in result:
            print(f"✅ Project added to watching: {result['result']}")
            
            # Create a test Python file
            test_file = Path(project_path) / "test.py"
            test_file.write_text("""
def hello_world():
    \"\"\"A simple hello world function\"\"\"
    print("Hello, World!")

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
""")
            
            # Wait a moment for file watching to pick up the change
            time.sleep(2)
            
            # List watched projects
            list_result = jsonrpc_call("tools/call", {
                "tool": "list_watched_projects"
            })
            
            if "result" in list_result:
                projects = list_result["result"]
                print(f"✅ Watched projects: {len(projects.get('active_projects', []))} projects")
                print(f"✅ Watch status: {projects.get('watch_status', {})}")
            
            # Remove project from watching
            remove_result = jsonrpc_call("tools/call", {
                "tool": "remove_project_watch",
                "params": {"project_path": project_path}
            })
            
            if "result" in remove_result:
                print(f"✅ Project removed from watching: {remove_result['result']}")
        else:
            print(f"❌ Project watching test failed: {result}")

def test_intelligent_symbol_search():
    """Test intelligent symbol search"""
    print("\n🔎 Testing Intelligent Symbol Search...")
    
    # Create a temporary project with multiple files
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = temp_dir
        
        # Create Python test file
        python_file = Path(project_path) / "example.py"
        python_file.write_text("""
class DatabaseManager:
    def __init__(self, connection_string):
        self.connection = connection_string
    
    def connect(self):
        pass
    
    def execute_query(self, query):
        pass

def process_data(data):
    return data.upper()

DATABASE_URL = "sqlite:///test.db"
""")
        
        # Create JavaScript test file
        js_file = Path(project_path) / "example.js"
        js_file.write_text("""
class UserManager {
    constructor(database) {
        this.db = database;
    }
    
    async getUser(id) {
        return await this.db.query('SELECT * FROM users WHERE id = ?', [id]);
    }
}

function processUser(user) {
    return {
        ...user,
        fullName: `${user.firstName} ${user.lastName}`
    };
}

const API_URL = 'https://api.example.com';
""")
        
        # Add project to watching first
        watch_result = jsonrpc_call("tools/call", {
            "tool": "add_project_watch",
            "params": {
                "project_path": project_path,
                "project_name": "search_test_project"
            }
        })
        
        if "result" in watch_result:
            # Wait for indexing
            time.sleep(3)
            
            # Search for symbols
            search_queries = ["Manager", "process", "URL"]
            
            for query in search_queries:
                result = jsonrpc_call("tools/call", {
                    "tool": "intelligent_symbol_search",
                    "params": {
                        "query": query,
                        "project_path": project_path,
                        "search_type": "all"
                    }
                })
                
                if "result" in result:
                    search_data = result["result"]
                    print(f"✅ Search '{query}': found {search_data.get('total_found', 0)} results")
                    
                    # Show top results
                    for i, res in enumerate(search_data.get('results', [])[:3]):
                        print(f"   {i+1}. {res.get('name', 'Unknown')} ({res.get('type', 'unknown')}) in {Path(res.get('file', res.get('file_path', 'unknown'))).name}")
                else:
                    print(f"❌ Search '{query}' failed: {result}")
            
            # Clean up
            jsonrpc_call("tools/call", {
                "tool": "remove_project_watch",
                "params": {"project_path": project_path}
            })

def test_project_aware_completions():
    """Test project-aware code completions"""
    print("\n💡 Testing Project-Aware Completions...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = temp_dir
        
        # Create a Python file with some context
        test_file = Path(project_path) / "completion_test.py"
        test_file.write_text("""
import os
import json

class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.cache = {}
    
    def process_file(self, filename):
        if filename in self.cache:
            return self.cache[filename]
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        result = self.transform_data(data)
        self.cache[filename] = result
        return result
    
    def transform_data(self, data):
        # User is typing here and wants completions
        return d
""")
        
        # Add project to watching
        watch_result = jsonrpc_call("tools/call", {
            "tool": "add_project_watch",
            "params": {
                "project_path": project_path,
                "project_name": "completion_test"
            }
        })
        
        if "result" in watch_result:
            # Wait for indexing
            time.sleep(2)
            
            # Request completions at the end of the file
            result = jsonrpc_call("tools/call", {
                "tool": "project_aware_complete",
                "params": {
                    "file_path": str(test_file),
                    "line": 25,
                    "column": 16,
                    "context": "return d",
                    "project_path": project_path
                }
            })
            
            if "result" in result:
                completion_data = result["result"]
                completions = completion_data.get("completions", [])
                context_info = completion_data.get("context_info", {})
                
                print(f"✅ Generated {len(completions)} completions")
                print(f"✅ Static analysis found {context_info.get('static_analysis_count', 0)} base completions")
                print(f"✅ Project has {context_info.get('project_symbols', 0)} total symbols")
                print(f"✅ Enhanced by LLM: {context_info.get('enhanced_by_llm', False)}")
                
                # Show top completions
                for i, comp in enumerate(completions[:5]):
                    print(f"   {i+1}. {comp.get('text', 'unknown')} ({comp.get('kind', 'unknown')}) - {comp.get('detail', 'no description')}")
            else:
                print(f"❌ Completion test failed: {result}")
            
            # Clean up
            jsonrpc_call("tools/call", {
                "tool": "remove_project_watch",
                "params": {"project_path": project_path}
            })

def test_health_check():
    """Test enhanced health check"""
    print("\n❤️  Testing Health Check...")
    
    try:
        response = requests.get(f"{MCP_SERVER_URL.rstrip('/')}/health")
        health_data = response.json()
        
        print(f"✅ Server status: {health_data.get('status', 'unknown')}")
        print(f"✅ Components: {health_data.get('components', {})}")
        print(f"✅ Features: {health_data.get('features', {})}")
        
        if "project_manager_details" in health_data:
            pm_details = health_data["project_manager_details"]
            print(f"✅ Watched projects: {len(pm_details.get('watched_projects', []))}")
            print(f"✅ Cached files: {pm_details.get('cached_files', 0)}")
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")

def main():
    """Run all tests"""
    print("🚀 Enhanced MCP Server Feature Tests")
    print("=" * 50)
    
    try:
        # Test if server is running
        response = requests.get(f"{MCP_SERVER_URL.rstrip('/')}/health", timeout=5)
        if response.status_code != 200:
            print("❌ MCP server is not responding. Please start the server first.")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to MCP server. Please start the server first.")
        print(f"   Expected URL: {MCP_SERVER_URL}")
        return
    
    # Run all tests
    test_health_check()
    test_language_support()
    test_project_watching()
    test_intelligent_symbol_search()
    test_project_aware_completions()
    
    print("\n🎉 All tests completed!")
    print("\nKey Features Demonstrated:")
    print("1. 📚 Rich Context: Project-aware completions with multi-source intelligence")
    print("2. ⚡ Real-time Updates: File watching and incremental indexing")
    print("3. 🔧 Extensible Architecture: Pluggable language support system")

if __name__ == "__main__":
    main() 