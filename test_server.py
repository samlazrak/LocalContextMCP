#!/usr/bin/env python3
"""
Test script to verify MCP server functionality
"""

import subprocess
import time
import requests
import json
import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required imports work"""
    print("🧪 Testing imports...")
    
    try:
        import flask
        import jsonrpcserver
        import pydantic
        import psycopg2
        import aiohttp
        import asyncpg
        import watchdog
        print("✅ All core imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def test_enhanced_modules():
    """Test that enhanced modules can be imported"""
    print("🧪 Testing enhanced modules...")
    
    try:
        from code_intelligence import code_intelligence
        from file_watcher import ProjectManager
        from language_support import extensible_code_intelligence
        print("✅ Enhanced modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Enhanced module import error: {e}")
        return False

def test_lmstudio_integration():
    """Test LM Studio integration module"""
    print("🧪 Testing LM Studio integration...")
    
    try:
        from lmstudio_integration import chat, complete, get_embedding
        print("✅ LM Studio integration imported successfully")
        return True
    except ImportError as e:
        print(f"❌ LM Studio integration error: {e}")
        return False

def start_server(server_file="mcp_server.py", port=8080):
    """Start the MCP server in background"""
    print(f"🚀 Starting server: {server_file}")
    
    try:
        process = subprocess.Popen([
            sys.executable, server_file
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Check if server is running
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Server started successfully on port {port}")
                return process
            else:
                print(f"❌ Server responded with status {response.status_code}")
                return None
        except requests.exceptions.RequestException:
            print("❌ Server not responding to health check")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def test_basic_endpoints(port=8080):
    """Test basic MCP endpoints"""
    print("🧪 Testing basic endpoints...")
    
    base_url = f"http://localhost:{port}"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False
    
    # Test tools/list
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        response = requests.post(f"{base_url}/", json=payload)
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                print(f"✅ tools/list working - found {len(data['result'])} tools")
            else:
                print(f"❌ tools/list no result: {data}")
                return False
        else:
            print(f"❌ tools/list failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ tools/list error: {e}")
        return False
    
    # Test simple tool call
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"tool": "time"},
            "id": 2
        }
        response = requests.post(f"{base_url}/", json=payload)
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                print("✅ Basic tool call working")
            else:
                print(f"❌ Tool call no result: {data}")
                return False
        else:
            print(f"❌ Tool call failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Tool call error: {e}")
        return False
    
    return True

def test_enhanced_features(port=8080):
    """Test enhanced features if available"""
    print("🧪 Testing enhanced features...")
    
    base_url = f"http://localhost:{port}"
    
    # Test language support
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"tool": "get_language_support"},
            "id": 3
        }
        response = requests.post(f"{base_url}/", json=payload)
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                print("✅ Enhanced language support working")
            else:
                print("⚠️ Enhanced features not available")
        else:
            print("⚠️ Enhanced features not available")
    except Exception as e:
        print(f"⚠️ Enhanced features test failed: {e}")

def main():
    """Main test function"""
    print("🚀 MCP Server Test Suite")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed - please install dependencies")
        return False
    
    # Test enhanced modules
    enhanced_available = test_enhanced_modules()
    
    # Test LM Studio integration
    lm_studio_available = test_lmstudio_integration()
    
    # Determine which server to test
    servers_to_test = []
    
    if enhanced_available:
        servers_to_test.append(("integrated_mcp_server.py", 8080))
        servers_to_test.append(("enhanced_mcp_server.py", 8081))
    
    servers_to_test.append(("mcp_server.py", 8082))
    
    success_count = 0
    
    for server_file, port in servers_to_test:
        if not os.path.exists(server_file):
            print(f"⚠️ Skipping {server_file} - file not found")
            continue
            
        print(f"\n🧪 Testing {server_file}")
        print("-" * 30)
        
        # Start server
        process = start_server(server_file, port)
        if not process:
            print(f"❌ Failed to start {server_file}")
            continue
        
        try:
            # Test basic endpoints
            if test_basic_endpoints(port):
                print(f"✅ {server_file} basic tests passed")
                success_count += 1
                
                # Test enhanced features if available
                if enhanced_available and "enhanced" in server_file:
                    test_enhanced_features(port)
            else:
                print(f"❌ {server_file} basic tests failed")
        
        finally:
            # Stop server
            process.terminate()
            process.wait()
            print(f"🛑 Stopped {server_file}")
    
    print(f"\n🎉 Test Summary: {success_count}/{len(servers_to_test)} servers working")
    
    if success_count > 0:
        print("\n✅ Repository is working!")
        print("\nTo start the server manually:")
        if enhanced_available:
            print("  python3 integrated_mcp_server.py  # Full featured")
        print("  python3 mcp_server.py             # Basic version")
        return True
    else:
        print("\n❌ Repository has issues that need to be fixed")
        return False

if __name__ == "__main__":
    main() 