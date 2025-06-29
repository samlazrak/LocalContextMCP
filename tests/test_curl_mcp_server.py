import subprocess
import json

def run_curl(json_data):
    cmd = [
        "curl", "-s", "-X", "POST", "http://localhost:8080/", 
        "-H", "Content-Type: application/json", 
        "-d", json.dumps(json_data)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def test_curl_tools_list():
    resp = run_curl({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
    data = json.loads(resp)
    assert "result" in data
    assert "git" in data["result"]
    assert "filesystem" in data["result"]

def test_curl_tools_call_time():
    resp = run_curl({"jsonrpc": "2.0", "method": "tools/call", "params": {"tool": "time"}, "id": 2})
    data = json.loads(resp)
    assert "result" in data

def test_curl_tools_call_git():
    resp = run_curl({"jsonrpc": "2.0", "method": "tools/call", "params": {"tool": "git", "params": {"command": "status"}}, "id": 3})
    data = json.loads(resp)
    assert "result" in data

def test_curl_tools_call_web_search():
    resp = run_curl({"jsonrpc": "2.0", "method": "tools/call", "params": {"tool": "web-search", "params": {"query": "openai"}}, "id": 4})
    data = json.loads(resp)
    assert "result" in data
    assert isinstance(data["result"], list)

def test_curl_resources_list():
    resp = run_curl({"jsonrpc": "2.0", "method": "resources/list", "id": 5})
    data = json.loads(resp)
    assert "result" in data
    assert isinstance(data["result"], list)

def test_curl_prompts_list():
    resp = run_curl({"jsonrpc": "2.0", "method": "prompts/list", "id": 6})
    data = json.loads(resp)
    assert "result" in data
    assert "greet" in data["result"]

def test_curl_prompts_get():
    resp = run_curl({"jsonrpc": "2.0", "method": "prompts/get", "params": {"prompt": "greet"}, "id": 7})
    data = json.loads(resp)
    assert "result" in data
    assert "Hello" in data["result"]

def test_curl_sampling_createMessage():
    resp = run_curl({"jsonrpc": "2.0", "method": "sampling/createMessage", "params": {"prompt": "greet", "context": "world"}, "id": 8})
    data = json.loads(resp)
    assert "result" in data
    assert "greet" in data["result"]
