import numpy as np
import os
import requests

LMSTUDIO_API_BASE = os.environ.get('LMSTUDIO_API_BASE', 'http://localhost:1234/v1')
LMSTUDIO_EMBEDDING_MODEL = os.environ.get('LMSTUDIO_EMBEDDING_MODEL', 'qwen2.5-coder-0.5B-instruct')

def get_embedding(text, api_base=LMSTUDIO_API_BASE, model=LMSTUDIO_EMBEDDING_MODEL):
    url = f"{api_base}/embeddings"
    payload = {
        "model": model,
        "input": [text]
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    embedding = response.json()['data'][0]['embedding']
    return np.array(embedding, dtype=np.float32)

if __name__ == '__main__':
    sample = "This is a test sentence."
    emb = get_embedding(sample)
    print(f"LM Studio embedding shape: {emb.shape}")
    print("Embedding generation module ready.") 