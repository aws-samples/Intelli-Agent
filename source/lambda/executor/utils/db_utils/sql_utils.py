from .athena_utils import create_athena_client, get_athena_query_result, schedule_athena_query
import logging
import time

def check_sql_validation(raw_query_string, db_name="cf_log_database", region="us-east-1", query_output="s3://text2sql-2024/athena_results/"):
    # format query
    try:
        query_string = raw_query_string.split("<query>")[1].split("</query>")[0]
    except:
        query_string = raw_query_string
    # print("Inside execute query", query_string)
    # query_result_folder='athena_query_output/'
    query_config = {"OutputLocation": f"{query_output}"}
    query_execution_context = {
        "Database": db_name,
    }
    # query_string="Explain  "+query_string
    logging.info(f"Executing: {query_string}")

    athena_client = create_athena_client(region)
    # schedule_result = schedule_athena_query(client, db_name, query_string, query_output)
    try:
        logging.info(" I am checking the syntax here")
        query_execution = athena_client.start_query_execution(
            QueryString=query_string,
            ResultConfiguration=query_config,
            QueryExecutionContext=query_execution_context,
        )
        execution_id = query_execution["QueryExecutionId"]
        logging.info(f"execution_id: {execution_id}")
        time.sleep(3)
        results = athena_client.get_query_execution(QueryExecutionId=execution_id)
        # print(f"results: {results}")
        status=results['QueryExecution']['Status']
        logging.info("Status :",status)
        if status['State']=='SUCCEEDED':
            return "Passed"
        else:  
            logging.info(results['QueryExecution']['Status']['StateChangeReason'])
            errmsg=results['QueryExecution']['Status']['StateChangeReason']
            return errmsg
        # return results
    except Exception as e:
        logging.info("Error in exception")
        msg = str(e)
        logging.info(msg)
    
if __name__ == "__main__":
    query_string = 'SELECT * FROM "cff_log_database"."cloudfront_standard_log" limit 10'
    check_sql_validation(query_string=query_string)

