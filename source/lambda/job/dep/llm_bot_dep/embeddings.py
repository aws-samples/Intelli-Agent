def get_embedding_info(embeddings_model_id):
    """
    Get the embedding info from the endpoint name
    """
    # Get the embedding info from the endpoint name
    if "bge-large-zh" in embeddings_model_id:
        embeddings_model_dimensions = 1024
    elif "bge-large-en" in embeddings_model_id:
        embeddings_model_dimensions = 1024
    elif "bge-m3" in embeddings_model_id:
        embeddings_model_dimensions = 1024
    elif "cohere" in embeddings_model_id:
        embeddings_model_dimensions = 1024
    elif "titan-embed-text-v1" in embeddings_model_id:
        embeddings_model_dimensions = 1536
    elif "titan-embed-text-v2" in embeddings_model_id:
        embeddings_model_dimensions = 1024
    elif "text-embedding-3-small" in embeddings_model_id:
        embeddings_model_dimensions = 1536
    elif "text-embedding-3-large" in embeddings_model_id:
        embeddings_model_dimensions = 3072
    elif "embedding" in embeddings_model_id:
        embeddings_model_dimensions = 768
    else:
        embeddings_model_dimensions = 1024

    return {
        "modelDimension": embeddings_model_dimensions,
    }
