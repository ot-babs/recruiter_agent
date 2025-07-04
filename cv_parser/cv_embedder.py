import openai

def chunk_cv(cv_dict, chunk_size=500):
    """
    Splits CV sections into chunks of at most `chunk_size` characters for embedding.
    """
    chunks = []
    for section, content in cv_dict.items():
        text = content
        # Split text into chunks
        while len(text) > chunk_size:
            split_idx = text[:chunk_size].rfind('\n')
            if split_idx == -1:
                split_idx = chunk_size
            chunks.append(f"{section.upper()}:\n{text[:split_idx]}")
            text = text[split_idx:]
        if text.strip():
            chunks.append(f"{section.upper()}:\n{text.strip()}")
    return chunks

def embed_cv(chunks, api_key):
    """
    Given a list of text chunks, returns their OpenAI embeddings.
    """
    openai.api_key = api_key
    embeddings = []
    for chunk in chunks:
        response = openai.embeddings.create(
            input=chunk,
            model="text-embedding-ada-002"
        )
        vector = response.data[0].embedding
        embeddings.append({"text": chunk, "embedding": vector})
    return embeddings