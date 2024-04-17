import logging
import time
import boto3

log = logging.getLogger(__name__)
log.setLevel("INFO")

SLEEP_TIME = 1
RETRY_COUNT = 60

def create_athena_client(region_name: str):
    """Singleton function to create an Athena client if not existed

    Args:
        region_name (str): region name

    Returns:
        Athena client
    """
    if "athena" not in boto3.Session().get_available_services():
        athena_client = boto3.client("athena", region_name=region_name)
        return athena_client
    else:
        log.info("[create_athena_client] Athena client already exists")
        return boto3.client("athena")

def get_athena_query_result(athena_client, query_execution_id: str):
    """Get query result by query execution id

    Args:
        athena_client: Athena client
        query_execution_id (str): Athena query execution id
    Returns:
        Query result
    """
    for i in range(1, 1 + RETRY_COUNT):
        # Get query execution
        query_status = athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )
        query_execution_status = query_status["QueryExecution"]["Status"]["State"]

        if query_execution_status == "SUCCEEDED":
            log.info(
                "[get_athena_query_result] STATUS: %s, retry: %s", 
                query_execution_status,
                str(i)
            )
            break
        if query_execution_status == "FAILED":
            raise Exception(
                "[get_athena_query_result] STATUS: "
                + query_execution_status
                + ", retry: "
                + str(i)
            )
        else:
            log.info(
                "[get_athena_query_result] STATUS: %s, retry: %s", 
                query_execution_status,
                str(i)
            )
            time.sleep(SLEEP_TIME)
    else:
        athena_client.stop_query_execution(QueryExecutionId=query_execution_id)
        raise Exception(
            "[get_athena_query_result] TIME OUT with retry: " + str(RETRY_COUNT)
        )

    # Get query results when succeed
    result = athena_client.get_query_results(QueryExecutionId=query_execution_id)
    log.info("[get_athena_query_result] Get query result: %s", str(result))

    return result

def schedule_athena_query(athena_client, db_name: str, query_string: str, query_output: str):
    """Schedule an athena query

    Args:
        athena_client: Athena client
        db_name (str): database name
        query_string (str): SQL sentence to be executed
        query_output (str): S3 path to store query output, eg. s3://<bucket_name>/output

    Returns:
        Query response
    """
    log.info("[schedule_athena_query] Query string: %s", query_string)

    response = athena_client.start_query_execution(
        QueryString=query_string,
        QueryExecutionContext={"Database": db_name},
        ResultConfiguration={
            "OutputLocation": query_output,
            "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"},
        },
        WorkGroup="primary",
    )

    return response
