"""
Schema definitions for ETL processing parameters.
"""
from typing import Optional

from pydantic import BaseModel, Field


class VLLMParameters(BaseModel):
    """
    Parameters for VLLM model configuration.
    
    This class encapsulates all parameters related to VLLM model configuration,
    allowing them to be passed around as a single unit.
    """
    model_provider: str = Field(
        description="The provider of the model (e.g., 'openai', 'anthropic')"
    )
    model_id: str = Field(
        description="The identifier for the specific model"
    )
    model_api_url: str = Field(
        description="The API URL endpoint for the model"
    )
    model_secret_name: str = Field(
        description="The name of the secret containing model credentials"
    )
    
    class Config:
        """Configuration for the VLLMParameters model."""
        validate_assignment = True
        extra = "forbid"  # Prevent additional fields not defined in the schema


class ProcessingParameters(BaseModel):
    """
    Parameters for ETL document processing operations.
    
    This class defines the standard parameters needed for document extraction,
    transformation, and loading operations across different file types.
    """
    source_bucket_name: str = Field(
        description="The S3 bucket containing the source document"
    )
    source_object_key: str = Field(
        description="The S3 key of the source document"
    )
    etl_endpoint_name: str = Field(
        description="The endpoint name for the ETL model service"
    )
    result_bucket_name: str = Field(
        description="The S3 bucket where processed results will be stored"
    )
    portal_bucket_name: Optional[str] = Field(
        default=None,
        description="Optional bucket name for portal-related storage"
    )
    document_language: str = Field(
        description="The language of the document (e.g., 'en', 'zh')"
    )
    file_type: str = Field(
        description="The type of the file (e.g., 'csv', 'xlsx', 'image')"
    )
    
    # Additional parameters for specific file types
    csv_rows_per_document: Optional[int] = Field(
        default=1,
        description="Number of rows to process for CSV files"
    )
    xlsx_rows_per_document: Optional[int] = Field(
        default=1,
        description="Number of rows to process for Excel files"
    )
    
    # VLLM parameters as a nested model
    vllm_parameters: Optional[VLLMParameters] = Field(
        default=None,
        description="Optional VLLM model parameters"
    )
    
    class Config:
        """Configuration for the ProcessingParameters model."""
        validate_assignment = True
        extra = "forbid"  # Prevent additional fields not defined in the schema 