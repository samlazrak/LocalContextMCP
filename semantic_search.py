import db
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def search_similar_chunks(query_embedding, session_id, top_k=3):
    conn = db.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, content, embedding FROM context_chunks WHERE session_id=%s AND embedding IS NOT NULL",
                    (session_id,)
                )
                results = []
                for row in cur.fetchall():
                    chunk_id, content, embedding_blob = row
                    embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                    sim = cosine_similarity(query_embedding, embedding)
                    results.append((sim, content))
        results.sort(reverse=True)
        return [content for sim, content in results[:top_k]]
    except Exception as e:
        print(f"Error in semantic search: {e}")
        raise
    finally:
        db.release_connection(conn)

# Example usage (requires actual embeddings)
if __name__ == '__main__':
    # Example: query_embedding = np.random.rand(384).astype(np.float32)
    pass 