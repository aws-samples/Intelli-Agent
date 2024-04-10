Excute the following commands to setup local Amazon Open Search running on docker.
'''
docker run -d -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" opensearchproject/opensearch:latest
'''

Create the specified index
'''
curl -XPUT "https://localhost:9200/\_cluster/settings" -k -u 'admin:admin' -H 'Content-Type: application/json' -d'
{
"persistent": {
"cluster.blocks.create_index": false
}
}'

curl -XPUT "https://localhost:9200/llm-bot-index" -k -u 'admin:admin' -H 'Content-Type: application/json' -d'
{
"settings": {
"index": {
"knn": true,
"knn.algo_param.ef_search": 512,
"refresh_interval": "60s",
"number_of_shards": 8,
"number_of_replicas": 0
}
},
"mappings": {
"properties": {
"vector_field": {
"type": "knn_vector",
"dimension": 1536,
"method": {
"name": "hnsw",
"space_type": "l2",
"engine": "nmslib",
"parameters": {
"ef_construction": 128,
"m": 16
}
}
}
}
}
}'
'''

Check if index actually indexed.
'''
curl -XGET "https://localhost:9200/\_search" -k -u 'admin:admin' -H 'Content-Type: application/json' -d'
{
"query": {
"match_all": {}
}
}'
'''

Remove the Read-Only Block in case the throttling error like [TOO_MANY_REQUESTS/12/disk usage exceeded flood-stage watermark, index has read-only-allow-delete block]'.
'''
curl -X PUT "http://localhost:9200/llm-bot-index/\_settings" -k -u 'admin:admin' -H "Content-Type: application/json" -d'
{
"index.blocks.read_only_allow_delete": false
}
'

du -ah -d 1 | sort -hr | head -n 10 //List disk usage sorted by size and remove the unwanted files to free up space.
'''

Delete the index and start over if needed if all index messed up.
'''
curl -X DELETE "https://localhost:9200/llm-bot-index" -ku 'admin:admin'
'''
