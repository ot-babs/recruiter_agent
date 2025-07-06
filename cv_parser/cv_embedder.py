from langchain_openai import OpenAIEmbeddings

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
    embeddings_model = OpenAIEmbeddings(
        openai_api_key=api_key,
        model="text-embedding-ada-002"
    )
    
    embeddings = []
    for chunk in chunks:
        vector = embeddings_model.embed_query(chunk)
        embeddings.append({"text": chunk, "embedding": vector})
    return embeddings