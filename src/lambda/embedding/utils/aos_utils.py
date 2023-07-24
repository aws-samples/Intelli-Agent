import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

credentials = boto3.Session().get_credentials()
region = boto3.Session().region_name
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

class OpenSearchClient:
    def __init__(self, host):
        """
        Initialize OpenSearch client using OpenSearch Endpoint
        """
        self.client = OpenSearch(
            hosts = [{'host': host.replace("https://", ""), 'port': 443}],
            http_auth = awsauth,
            use_ssl = True,
            verify_certs = True,
            connection_class = RequestsHttpConnection,
            region=region
        )