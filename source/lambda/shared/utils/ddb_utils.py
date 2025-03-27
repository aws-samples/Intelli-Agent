import os
from typing import Any, Dict, Optional

import boto3


def get_item(ddb_table: boto3.resource, key: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic function to get an item from any DynamoDB table
    
    Args:
        table_name: Name of the DynamoDB table
        key: Key to identify the item in DynamoDB format (e.g., {"id": {"S": "value"}})
        
    Returns:
        The item as a dictionary
        
    """
    response = ddb_table.get_item(
        Key=key
    )
    if "Item" not in response:
        return None
    return response["Item"]
