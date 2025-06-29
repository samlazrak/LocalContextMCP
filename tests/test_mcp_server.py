import requests
import os
import tempfile

BASE_URL = "http://localhost:8080/"

def jsonrpc(method, params=None, id=1):
    req = {"jsonrpc": "2.0", "method": method, "id": id}
    if params is not None:
        req["params"] = params
    return req

def test_tools_list():
    resp = requests.post(BASE_URL, json=jsonrpc("tools/list"))
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert "git" in result
    assert "filesystem" in result

def test_tools_call_time():
    resp = requests.post(BASE_URL, json=jsonrpc("tools/call", {"tool": "time"}))
    assert resp.status_code == 200
    assert "result" in resp.json()

def test_tools_call_git():
    resp = requests.post(BASE_URL, json=jsonrpc("tools/call", {"tool": "git", "params": {"command": "status"}}))
    assert resp.status_code == 200
    assert "result" in resp.json()

def test_tools_call_sqlite():
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        resp = requests.post(BASE_URL, json=jsonrpc("tools/call", {
            "tool": "sqlite",
            "params": {"db_path": tf.name, "query": "CREATE TABLE t(x int);"}
        }))
        assert resp.status_code == 200
        resp = requests.post(BASE_URL, json=jsonrpc("tools/call", {
            "tool": "sqlite",
            "params": {"db_path": tf.name, "query": "SELECT name FROM sqlite_master WHERE type='table';"}
        }))
        assert resp.status_code == 200
        assert "t" in str(resp.json()["result"])

def test_tools_call_filesystem(tmp_path):
    testfile = tmp_path / "test.txt"
    testfile.write_text("hello")
    # List
    resp = requests.post(BASE_URL, json=jsonrpc("tools/call", {"tool": "filesystem", "params": {"action": "list"}}))
    assert resp.status_code == 200
    # Write
    resp = requests.post(BASE_URL, json=jsonrpc("tools/call", {"tool": "filesystem", "params": {"action": "write", "filename": "test2.txt", "content": "abc"}}))
    assert resp.status_code == 200
    # Read
    resp = requests.post(BASE_URL, json=jsonrpc("tools/call", {"tool": "filesystem", "params": {"action": "read", "filename": "test2.txt"}}))
    assert resp.status_code == 200
    assert resp.json()["result"] == "abc"

def test_tools_call_web_search():
    resp = requests.post(BASE_URL, json=jsonrpc("tools/call", {"tool": "web-search", "params": {"query": "openai"}}))
    assert resp.status_code == 200
    assert isinstance(resp.json()["result"], list)

def test_resources_list():
    resp = requests.post(BASE_URL, json=jsonrpc("resources/list"))
    assert resp.status_code == 200
    assert isinstance(resp.json()["result"], list)

def test_prompts_list():
    resp = requests.post(BASE_URL, json=jsonrpc("prompts/list"))
    assert resp.status_code == 200
    assert "greet" in resp.json()["result"]

def test_prompts_get():
    resp = requests.post(BASE_URL, json=jsonrpc("prompts/get", {"prompt": "greet"}))
    assert resp.status_code == 200
    assert "Hello" in resp.json()["result"]

def test_sampling_createMessage():
    resp = requests.post(BASE_URL, json=jsonrpc("sampling/createMessage", {"prompt": "greet", "context": "world"}))
    assert resp.status_code == 200
    assert "greet" in resp.json()["result"] 