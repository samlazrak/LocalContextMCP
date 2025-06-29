import db

def store_message(user_id, session_id, role, content):
    conn = db.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO messages (user_id, session_id, role, content) VALUES (%s, %s, %s, %s) RETURNING id",
                    (user_id, session_id, role, content)
                )
                message_id = cur.fetchone()[0]
        return message_id
    except Exception as e:
        print(f"Error storing message: {e}")
        raise
    finally:
        db.release_connection(conn)

def store_context_chunk(session_id, chunk_index, content, embedding=None, message_id=None, start_offset=None, end_offset=None):
    conn = db.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO context_chunks (session_id, chunk_index, content, embedding, message_id, start_offset, end_offset)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (session_id, chunk_index, content, embedding, message_id, start_offset, end_offset)
                )
    except Exception as e:
        print(f"Error storing context chunk: {e}")
        raise
    finally:
        db.release_connection(conn)

def get_recent_chunks(session_id, limit=5):
    conn = db.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM context_chunks WHERE session_id=%s ORDER BY chunk_index DESC LIMIT %s",
                    (session_id, limit)
                )
                results = [row[0] for row in cur.fetchall()]
        return results
    except Exception as e:
        print(f"Error retrieving recent chunks: {e}")
        raise
    finally:
        db.release_connection(conn)

# Example usage
if __name__ == '__main__':
    mid = store_message('user1', 'sess1', 'user', 'Hello!')
    store_context_chunk('sess1', 0, 'This is a chunk of context.', message_id=mid, start_offset=0, end_offset=24)
    print(get_recent_chunks('sess1')) 