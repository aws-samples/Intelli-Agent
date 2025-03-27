import json
import os
from typing import Any, Dict, List, Optional

import boto3
from pydantic import BaseModel
from shared.constant import ContextExtendMethod, Threshold
from shared.langchain_integration.retrievers.opensearch_retrievers import (
    OpensearchHybridQueryDocumentRetriever,
)
from shared.utils.ddb_utils import get_item
from shared.utils.logger_utils import get_logger

ddb_resource = boto3.resource("dynamodb")
model_table = ddb_resource.Table(os.environ["MODEL_TABLE_NAME"])
index_table = ddb_resource.Table(os.environ["INDEX_TABLE_NAME"])

logger = get_logger(__name__)


resp_header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
}


# Keep minimal Pydantic models for request/response validation
class KnowledgeBaseRequest(BaseModel):
    """Request schema for knowledge base search"""

    searchEngine: str
    indexName: str
    searchMode: str
    vectorSearchTopK: int
    bm25SearchTopK: int
    useRerank: bool = True
    rerankConfig: Optional[Dict] = None
    hideMetadataDetails: bool = (
        True  # Parameter to hide certain metadata details
    )
    query: str  # Add query to the request model


class Document(BaseModel):
    """Document schema for search results"""

    id: str
    paragraph: str
    metadata: Dict


class KnowledgeBaseResponse(BaseModel):
    """Response schema for knowledge base search results"""

    doc: List[Document]


def get_model_from_ddb(group_name: str, index_id: str) -> Dict[str, Any]:
    """
    Get embedding model configuration from DynamoDB

    Args:
        index_id: The index ID to look up

    Returns:
        Embedding model configuration
    """
    # Get index item from DynamoDB
    index_item = get_item(
        index_table, {"groupName": group_name, "indexId": index_id}
    )

    # Extract embedding model ID
    model_ids = index_item.get("modelIds", {})
    embedding_model_id = model_ids.get("embedding")
    rerank_model_id = model_ids.get("rerank")

    if not embedding_model_id:
        raise ValueError(f"No embedding model ID found for index {index_id}")
    if not rerank_model_id:
        raise ValueError(f"No rerank model ID found for index {index_id}")

    # Get embedding model details
    embedding_model_item = get_item(
        model_table, {"groupName": group_name, "modelId": embedding_model_id}
    )
    rerank_model_item = get_item(
        model_table, {"groupName": group_name, "modelId": rerank_model_id}
    )

    # Extract model parameters
    embedding_params = embedding_model_item.get("parameter", {})
    rerank_params = rerank_model_item.get("parameter", {})

    embedding_config = {
        "provider": embedding_params.get("modelProvider"),
        "model_id": embedding_params.get("modelId"),
        "base_url": embedding_params.get("baseUrl", ""),
        "api_key_arn": embedding_params.get("apiKeyArn", ""),
        "sagemaker_endpoint_name": embedding_params.get("modelEndpoint"),
        "sagemaker_target_model": embedding_params.get("targetModel", ""),
        "model_kwargs": {},
        "embedding_dimension": embedding_params.get("modelDimension", 1024),
    }

    rerank_config = {
        "provider": rerank_params.get("modelProvider"),
        "model_id": rerank_params.get("modelId"),
        "base_url": rerank_params.get("baseUrl", ""),
        "api_key_arn": rerank_params.get("apiKeyArn", ""),
        "sagemaker_endpoint_name": rerank_params.get("modelEndpoint"),
        "sagemaker_target_model": rerank_params.get("targetModel", ""),
        "model_kwargs": {},
    }
    return embedding_config, rerank_config


def initialize_retriever(
    group_name: str,
    request: KnowledgeBaseRequest,
) -> OpensearchHybridQueryDocumentRetriever:
    """
    Initialize the retriever based on request parameters

    Args:
        request: KnowledgeBaseRequest containing search parameters

    Returns:
        Initialized retriever
    """
    embedding_config, rerank_config_from_ddb = get_model_from_ddb(
        group_name, request.indexName
    )

    # Handle rerank configuration logic
    final_rerank_config = None
    if request.useRerank:
        if request.rerankConfig:
            # Validate the provided rerank config
            required_fields = ["rerankModelProvider", "rerankModelId"]
            missing_fields = [
                field
                for field in required_fields
                if field not in request.rerankConfig
            ]

            if missing_fields:
                raise ValueError(
                    f"Missing required fields in rerankConfig: {', '.join(missing_fields)}"
                )

            # Convert to our internal format
            provider = request.rerankConfig.get("rerankModelProvider")
            model_id = request.rerankConfig.get("rerankModelId")

            final_rerank_config = {
                "provider": provider,
                "model_id": model_id,
                "base_url": request.rerankConfig.get("baseUrl", ""),
                "api_key_arn": request.rerankConfig.get("apiKeyArn", ""),
                "sagemaker_endpoint_name": request.rerankConfig.get(
                    "reRankModelEndpoint"
                ),
                "sagemaker_target_model": request.rerankConfig.get(
                    "targetModel", ""
                ),
                "model_kwargs": {},
            }
        else:
            final_rerank_config = rerank_config_from_ddb
    else:
        # No reranking if useRerank is False
        final_rerank_config = None

    # Create base configuration
    base_config = {
        "index_name": request.indexName,
        "text_field": "text",
        "vector_field": "vector_field",
        "source_field": "file_path",
        "bm25_search_top_k": request.bm25SearchTopK,
        "vector_search_top_k": request.vectorSearchTopK,
        "bm25_search_context_extend_method": ContextExtendMethod.WHOLE_DOC,
        "vector_search_context_extend_method": ContextExtendMethod.WHOLE_DOC,
        "bm25_search_threshold": Threshold.BM25_SEARCH_THRESHOLD,
        "vector_search_threshold": Threshold.VECTOR_SEARCH_THRESHOLD,
        "enable_bm25_search": request.searchMode in ["keywords", "mix"],
        "enable_vector_search": request.searchMode in ["vector", "mix"],
    }

    # Create and return retriever
    return OpensearchHybridQueryDocumentRetriever.from_config(
        embedding_config=embedding_config,
        rerank_config=final_rerank_config,
        **base_config,
    )


def search(
    group_name: str, request: KnowledgeBaseRequest
) -> KnowledgeBaseResponse:
    """
    Search the knowledge base using the provided request parameters and query

    Args:
        request: KnowledgeBaseRequest containing search parameters and query

    Returns:
        KnowledgeBaseResponse containing the retrieved documents
    """
    retriever = initialize_retriever(group_name, request)

    # Perform search
    docs = retriever._get_relevant_documents(request.query, run_manager=None)

    # Convert docs to response format
    response_docs = []
    for doc in docs:
        # Create a copy of metadata to avoid modifying the original
        metadata = doc.metadata.copy()

        # If hideMetadataDetails is True, remove certain metadata details
        if request.hideMetadataDetails:
            metadata.pop("extend_chunks", None)
            metadata.pop("detail", None)

        response_docs.append(
            Document(
                id=doc.id,
                paragraph=doc.page_content,
                metadata=metadata,
            )
        )

    return KnowledgeBaseResponse(doc=response_docs)


def lambda_handler(event, context):
    """
    AWS Lambda handler function

    Args:
        event: Lambda event containing request body
        context: Lambda context

    Returns:
        Lambda response containing search results
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Get user information from authorizer
        authorizer_type = (
            event["requestContext"].get("authorizer", {}).get("authorizerType")
        )
        if authorizer_type == "lambda_authorizer":
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])

        if "use_api_key" in claims:
            group_name = get_query_parameter(event, "GroupName", "Admin")
        else:
            group_name = claims[
                "cognito:groups"
            ]  # Assume user is in only one group

        # Extract request body
        request_body = json.loads(event["body"])

        # Create request object
        request = KnowledgeBaseRequest(**request_body)

        # Perform search
        response = search(group_name, request)

        # Return results
        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(response.dict()),
        }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps({"error": str(e)}),
        }
