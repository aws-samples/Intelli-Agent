def get_embedding_info(embeddings_model_id):
    """
    Get the embedding info from the endpoint name
    """
    # Get the embedding info from the endpoint name
    if "bge-large-zh" in embeddings_model_id:
        embeddings_model_provider = "SageMaker"
        embeddings_model_id = "bge-large-zh-v1-5"
        embeddings_model_dimensions = 1024
    elif "bge-large-en" in embeddings_model_id:
        embeddings_model_provider = "SageMaker"
        embeddings_model_id = "bge-large-en-v1-5"
        embeddings_model_dimensions = 1024
    elif "bge-m3" in embeddings_model_id:
        embeddings_model_provider = "SageMaker"
        embeddings_model_id = "bge-m3"
        embeddings_model_dimensions = 1024
    elif "cohere" in embeddings_model_id:
        embeddings_model_provider = "Bedrock"
        embeddings_model_id = "cohere.embed-english-v3"
        embeddings_model_dimensions = 1024
    elif "titan-embed-text-v1" in embeddings_model_id:
        embeddings_model_provider = "Bedrock"
        embeddings_model_id = "amazon.titan-embed-text-v1"
        embeddings_model_dimensions = 1536
    elif "titan-embed-text-v2" in embeddings_model_id:
        embeddings_model_provider = "Bedrock"
        embeddings_model_id = "amazon.titan-embed-text-v2:0"
        embeddings_model_dimensions = 1024
    elif "text-embedding-3-small" in embeddings_model_id:
        embeddings_model_provider = "OpenAI API"
        embeddings_model_id = "text-embedding-3-small"
        embeddings_model_dimensions = 1536
    elif "text-embedding-3-large" in embeddings_model_id:
        embeddings_model_provider = "OpenAI API"
        embeddings_model_id = "text-embedding-3-large"
        embeddings_model_dimensions = 3072
    elif "embedding" in embeddings_model_id:
        embeddings_model_provider = "SageMaker"
        embeddings_model_id = "bce_embedding_model.tar.gz"
        embeddings_model_dimensions = 768
    else:
        embeddings_model_provider = "Not Found"
        embeddings_model_id = "Not Found"
        embeddings_model_dimensions = 1024

    return {
        "ModelProvider": embeddings_model_provider,
        "ModelId": embeddings_model_id,
        "ModelDimension": embeddings_model_dimensions,
    }
