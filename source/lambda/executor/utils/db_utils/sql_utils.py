from .athena_utils import create_athena_client, get_athena_query_result, schedule_athena_query
import logging
import time
import pandas as pd
import redshift_connector

def athena_run_and_check(query_string, db_name="cf_log_database", region="us-west-2", query_output="s3://text2sql-2024/athena_results/"):
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
        return msg

def redshift_run_and_check(query):
    """
    Query the database
    """
    RDS_MYSQL_HOST = 'clickstream-game-bi-demo.432014048474.us-west-2.redshift-serverless.amazonaws.com'
    RDS_MYSQL_PORT = '5439'
    RDS_MYSQL_DBNAME = 'game_bi_demo'
    RDS_MYSQL_USERNAME = 'clickstream_bi_b6uqhdw4'
    RDS_MYSQL_PASSWORD = 'iF3!bI72LYSCEfA^83b%yTnePq1=_YUw'
    # redshift_schema = 'zenmakeovermatch'
    # S3 bucket and prefix details
    # bucket_name = 'clickstream-gamebi'
    # prefix = 'customer_sample_data'  # Set to ‘’ if no prefix
    p_db_url = "postgresql+psycopg2://{RDS_MYSQL_USERNAME}:{RDS_MYSQL_PASSWORD}@{RDS_MYSQL_HOST}:{RDS_MYSQL_PORT}/{RDS_MYSQL_DBNAME}"
    p_db_url = p_db_url.format(RDS_MYSQL_HOST=RDS_MYSQL_HOST,
        RDS_MYSQL_PORT=RDS_MYSQL_PORT,
        RDS_MYSQL_USERNAME=RDS_MYSQL_USERNAME,
        RDS_MYSQL_PASSWORD=RDS_MYSQL_PASSWORD,
        RDS_MYSQL_DBNAME=RDS_MYSQL_DBNAME)
    try:
        conn = redshift_connector.connect(
            host = RDS_MYSQL_HOST,
            database = RDS_MYSQL_DBNAME,
            port = RDS_MYSQL_PORT,
            user = RDS_MYSQL_USERNAME,
            password = RDS_MYSQL_PASSWORD)

        logging.info(f'{query=}')
        cursor = conn.cursor()
        
        cursor.execute(query)
        # uncomment the following for debug purpose
        # result: tuple = cursor.fetchall()
        # columns = list(cursor.keys())
        # logging.info(f'---------got sql results-------------')
        # logging.info(f'{rows=}')
        # logging.info(f'{columns=}')
        # results_df = pd.DataFrame(result, columns=columns)
        # result_df = None
        return "Passed"
    except ValueError as e:
        logging.exception(e)
        error_message = e
        return error_message


# def redshift_run_and_check(query_string):
#     #  Redshift connection details
#     redshift_host = 'clickstream-game-bi-demo.432014048474.us-west-2.redshift-serverless.amazonaws.com'
#     redshift_port = '5439'
#     redshift_database = 'game_bi_demo'
#     redshift_user = 'clickstream_bi_b6uqhdw4'
#     redshift_password = 'iF3!bI72LYSCEfA^83b%yTnePq1=_YUw'
#     redshift_schema = 'zenmakeovermatch'
#     # S3 bucket and prefix details
#     bucket_name = 'clickstream-gamebi'
#     prefix = 'customer_sample_data'  # Set to ‘’ if no prefix
#     # Connect to Redshift
#     conn = psycopg2.connect(
#         host=redshift_host,
#         port=redshift_port,
#         database=redshift_database,
#         user=redshift_user,
#         password=redshift_password
#     )
#     try:
#         logging.info(" I am checking the syntax here")
#         cur = conn.cursor()
#         return cur
#     except Exception as e:
#         logging.info("Error in exception")
#         msg = str(e)
#         logging.info(msg)
#         return msg

def check_sql_validation(raw_query_string):
    # format query
    try:
        query_string = raw_query_string.split("<query>")[1].split("</query>")[0]
    except:
        query_string = raw_query_string
    
    # # check sql in athena
    # return athena_run_and_check(query_string)

    # check sql in redshift
    return redshift_run_and_check(query_string)
    
if __name__ == "__main__":
    query_string = 'SELECT * FROM "cff_log_database"."cloudfront_standard_log" limit 10'
    check_sql_validation(query_string=query_string)

