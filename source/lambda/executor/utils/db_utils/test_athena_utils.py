from athena_utils import create_athena_client, get_athena_query_result, schedule_athena_query

db_name = "cf_log_database"
query_string = 'SELECT * FROM "cf_log_database"."cloudfront_standard_log" limit 10'
query_output = "s3://<replace_with_your_bucket>/athena_results/"

client = create_athena_client("us-east-1")
schedule_result = schedule_athena_query(client, db_name, query_string, query_output)
query_id = schedule_result["QueryExecutionId"]
print("Query id: %s", query_id)
query_result = get_athena_query_result(client, query_id)
print("Query result: %s", str(query_result))
