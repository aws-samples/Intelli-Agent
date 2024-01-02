import psycopg2
import logging
from opensearchpy import OpenSearch

logger = logging.getLogger()
# logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)
logger.setLevel(logging.INFO)

def connect_to_rds(host, database, user, password):
    conn = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password
    )
    return conn

def extract_data(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM your_table")  # Adjust SQL query as needed
    rows = cur.fetchall()
    cur.close()
    return rows

def split_data(data, chunk_size):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]
    # TODO, using existing library of glue dep

def send_to_embedding_model(chunk):
    # This function needs to be implemented based on your embedding model.
    # For example, if your model is hosted as a REST API:
    # response = requests.post(model_url, json=chunk)
    # return response.json()
    pass

def ingest_to_opensearch(host, port, data):
    client = OpenSearch(
        hosts=[{'host': host, 'port': port}],
        http_compress=True,
        http_auth=('user', 'password'),
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )

    for record in data:
        # Assuming each record has an 'id' and 'vector' field
        index_response = client.index(
            index="your_index",
            body=record,
            id=record['id']
        )
        print(index_response)

def batch_entry():
    logger.info("Starting batch job...")
    # Define your RDS and OpenSearch credentials and endpoints
    rds_host = "your_rds_host"
    rds_db = "your_db_name"
    rds_user = "your_user"
    rds_password = "your_password"

    opensearch_host = "your_opensearch_host"
    opensearch_port = 443  # Typically 443 for HTTPS

    conn = connect_to_rds(rds_host, rds_db, rds_user, rds_password)
    data = extract_data(conn)
    conn.close()

    chunk_size = 100  # Define your chunk size
    for chunk in split_data(data, chunk_size):
        vectors = send_to_embedding_model(chunk)
        ingest_to_opensearch(opensearch_host, opensearch_port, vectors)

if __name__ == "__main__":
    batch_entry()
