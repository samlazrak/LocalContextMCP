from flask import Flask, request, jsonify
import store_and_retrieve
import semantic_search
import embedding
import numpy as np
import logging
from flasgger import Swagger

app = Flask(__name__)
Swagger(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint
    ---
    responses:
      200:
        description: Server is healthy
    """
    return jsonify({'status': 'ok'})

@app.route('/message', methods=['POST'])
def store_message():
    """Store a chat message
    ---
    parameters:
      - in: body
        name: message
        schema:
          type: object
          required: [user_id, session_id, role, content]
          properties:
            user_id:
              type: string
            session_id:
              type: string
            role:
              type: string
            content:
              type: string
    responses:
      200:
        description: Message stored
      400:
        description: Invalid input
      500:
        description: Server error
    """
    data = request.json
    required = ['user_id', 'session_id', 'role', 'content']
    if not data or not all(k in data for k in required):
        logger.warning('Missing required fields in /message')
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        message_id = store_and_retrieve.store_message(
            data['user_id'], data['session_id'], data['role'], data['content']
        )
        logger.info(f"Stored message {message_id}")
        return jsonify({'status': 'stored', 'message_id': message_id})
    except Exception as e:
        logger.error(f"Error storing message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/context_chunk', methods=['POST'])
def store_context_chunk():
    """Store a context chunk
    ---
    parameters:
      - in: body
        name: chunk
        schema:
          type: object
          required: [session_id, chunk_index, content]
          properties:
            session_id:
              type: string
            chunk_index:
              type: integer
            content:
              type: string
            embedding:
              type: array
              items:
                type: number
            message_id:
              type: integer
            start_offset:
              type: integer
            end_offset:
              type: integer
    responses:
      200:
        description: Chunk stored
      400:
        description: Invalid input
      500:
        description: Server error
    """
    data = request.json
    required = ['session_id', 'chunk_index', 'content']
    if not data or not all(k in data for k in required):
        logger.warning('Missing required fields in /context_chunk')
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        embedding_arr = None
        if 'embedding' in data and data['embedding'] is not None:
            embedding_arr = np.array(data['embedding'], dtype=np.float32).tobytes()
        store_and_retrieve.store_context_chunk(
            data['session_id'],
            data['chunk_index'],
            data['content'],
            embedding=embedding_arr,
            message_id=data.get('message_id'),
            start_offset=data.get('start_offset'),
            end_offset=data.get('end_offset')
        )
        logger.info(f"Stored context chunk for session {data['session_id']} index {data['chunk_index']}")
        return jsonify({'status': 'stored'})
    except Exception as e:
        logger.error(f"Error storing context chunk: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/recent_chunks', methods=['GET'])
def recent_chunks():
    """Retrieve recent context chunks
    ---
    parameters:
      - in: query
        name: session_id
        type: string
        required: true
      - in: query
        name: limit
        type: integer
        required: false
    responses:
      200:
        description: List of recent chunks
      400:
        description: Invalid input
      500:
        description: Server error
    """
    session_id = request.args.get('session_id')
    limit = request.args.get('limit', 5)
    if not session_id:
        logger.warning('Missing session_id in /recent_chunks')
        return jsonify({'error': 'Missing session_id'}), 400
    try:
        chunks = store_and_retrieve.get_recent_chunks(session_id, int(limit))
        return jsonify({'chunks': chunks})
    except Exception as e:
        logger.error(f"Error retrieving recent chunks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/semantic_search', methods=['POST'])
def semantic_search_endpoint():
    """Semantic search for similar context chunks
    ---
    parameters:
      - in: body
        name: search
        schema:
          type: object
          required: [session_id, query]
          properties:
            session_id:
              type: string
            query:
              type: string
            top_k:
              type: integer
    responses:
      200:
        description: List of similar chunks
      400:
        description: Invalid input
      500:
        description: Server error
    """
    data = request.json
    required = ['session_id', 'query']
    if not data or not all(k in data for k in required):
        logger.warning('Missing required fields in /semantic_search')
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        session_id = data['session_id']
        query_text = data['query']
        top_k = data.get('top_k', 3)
        query_embedding = embedding.get_embedding(query_text)
        results = semantic_search.search_similar_chunks(query_embedding, session_id, top_k=top_k)
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 