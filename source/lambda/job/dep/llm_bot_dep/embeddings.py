def get_embedding_info(embedding_endpoint_name):
    """
    Get the embedding info from the endpoint name
    """
    # Get the embedding info from the endpoint name
    if "bge-large-zh" in embedding_endpoint_name:
        embeddings_model_provider = "BAAI"
        embeddings_model_name = "bge-large-zh-v1-5"
        embeddings_model_dimensions = 1024
        embeddings_model_type = "bge-large-zh"

    elif "bge-large-en" in embedding_endpoint_name:
        embeddings_model_provider = "BAAI"
        embeddings_model_name = "bge-large-en-v1-5"
        embeddings_model_dimensions = 1024
        embeddings_model_type = "bge-large-en"

    elif "bge-m3" in embedding_endpoint_name:
        embeddings_model_provider = "BAAI"
        embeddings_model_name = "bge-m3"
        embeddings_model_dimensions = 1024
        embeddings_model_type = "m3"

    elif "embedding" in embedding_endpoint_name:
        embeddings_model_provider = "Netease"
        embeddings_model_name = "bce_embedding_model.tar.gz"
        embeddings_model_dimensions = 768
        embeddings_model_type = "bce"

    else:
        embeddings_model_provider = "Not Found"
        embeddings_model_name = "Not Found"
        embeddings_model_dimensions = 1024
        embeddings_model_type = "Not Found"

    return (
        embeddings_model_provider,
        embeddings_model_name,
        embeddings_model_dimensions,
        embeddings_model_type,
    )
