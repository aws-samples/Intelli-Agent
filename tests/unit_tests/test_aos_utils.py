import pytest
from lambda.aos.utils.aos_utils import OpenSearchClient  # This import assumes the PYTHONPATH in Makefile is set correctly

@pytest.fixture(scope="module")
# init the OpenSearchClient with local OpenSearch instance pulled from docker command
def opensearch_client():
    client = OpenSearchClient(_opensearch_cluster_domain="http://localhost:9200")
    yield client

def test_create_index(opensearch_client):
    index = "test-index"
    body = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
    }
    response = opensearch_client.create_index(index, body, {})
    assert response["acknowledged"] == True

def test_delete_index(opensearch_client):
    index = "test-index"
    response = opensearch_client.delete_index(index, "", {})
    assert response["acknowledged"] == True



