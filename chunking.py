def chunk_text(text, chunk_size=2048, overlap=256):
    """
    Splits text into overlapping chunks and returns a list of dicts with chunk content and metadata.
    Each dict contains: content, start_offset, end_offset
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = {
            'content': text[start:end],
            'start_offset': start,
            'end_offset': end
        }
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

# Example usage
if __name__ == '__main__':
    sample = "This is a long text..." * 200
    for i, chunk in enumerate(chunk_text(sample)):
        print(f"Chunk {i}: {chunk['content'][:60]}... (start: {chunk['start_offset']}, end: {chunk['end_offset']})") 