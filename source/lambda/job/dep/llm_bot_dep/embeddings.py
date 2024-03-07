def get_embedding_info(embedding_endpoint_name):
    """
    Get the embedding info from the endpoint name
    """
    # Get the embedding info from the endpoint name
    if "bge-large-zh" in embedding_endpoint_name:
        embeddings_model_provider = "BAAI"
        embeddings_model_name = "bge-large-zh-v1-5"
        embeddings_model_dimensions = 1024

    elif "bge-large-en" in embedding_endpoint_name:
        embeddings_model_provider = "BAAI"
        embeddings_model_name = "bge-large-en-v1-5"
        embeddings_model_dimensions = 1024
    
    elif "bge-m3" in embedding_endpoint_name:
        embeddings_model_provider = "BAAI"
        embeddings_model_name = "bge-m3"
        embeddings_model_dimensions = 1024

    else:
        embeddings_model_provider = "Not Found"
        embeddings_model_name = "Not Found"
        embeddings_model_dimensions = 1024

    return (
        embeddings_model_provider,
        embeddings_model_name,
        embeddings_model_dimensions,
    )
