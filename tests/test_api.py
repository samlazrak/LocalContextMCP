import requests
import pytest

BASE_URL = 'http://localhost:5000'

@pytest.fixture(scope='module')
def session_id():
    return 'testsession'

@pytest.fixture(scope='module')
def message_id(session_id):
    data = {
        'user_id': 'testuser',
        'session_id': session_id,
        'role': 'user',
        'content': 'Hello, world!'
    }
    resp = requests.post(f'{BASE_URL}/message', json=data)
    assert resp.status_code == 200
    return resp.json()['message_id']

def test_health():
    resp = requests.get(f'{BASE_URL}/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'

def test_store_message(session_id):
    data = {
        'user_id': 'testuser2',
        'session_id': session_id,
        'role': 'assistant',
        'content': 'Hi!'
    }
    resp = requests.post(f'{BASE_URL}/message', json=data)
    assert resp.status_code == 200
    assert 'message_id' in resp.json()

def test_store_context_chunk(session_id, message_id):
    data = {
        'session_id': session_id,
        'chunk_index': 0,
        'content': 'Chunk content',
        'embedding': [0.1] * 384,
        'message_id': message_id,
        'start_offset': 0,
        'end_offset': 12
    }
    resp = requests.post(f'{BASE_URL}/context_chunk', json=data)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'stored'

def test_recent_chunks(session_id):
    resp = requests.get(f'{BASE_URL}/recent_chunks', params={'session_id': session_id, 'limit': 2})
    assert resp.status_code == 200
    assert 'chunks' in resp.json()

def test_semantic_search(session_id):
    data = {
        'session_id': session_id,
        'query': 'Chunk',
        'top_k': 1
    }
    resp = requests.post(f'{BASE_URL}/semantic_search', json=data)
    assert resp.status_code == 200
    assert 'results' in resp.json() 