"""
Schema definitions for ETL processing parameters.
"""
from typing import Optional

from pydantic import BaseModel, Field


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
    
    class Config:
        """Configuration for the ProcessingParameters model."""
        validate_assignment = True
        extra = "forbid"  # Prevent additional fields not defined in the schema 