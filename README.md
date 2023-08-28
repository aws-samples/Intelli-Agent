## LLM Bot

![image](https://github.com/aws-samples/llm-bot/assets/23544182/68a37d9b-e3bf-4737-9c76-7632c3f5d3ef)

### Quick Start

1. Prepare model assets by executing script per model folder
```bash
% cd src/models/<cross/embedding/instruct>/model
% ./model.sh       
Make sure Python installed properly. Usage: ./model.sh -t TOKEN [-m MODEL_NAME] [-c COMMIT_HASH] [-s S3_BUCKET_NAME]
  -t TOKEN            Hugging Face token (required)
  -m MODEL_NAME       Model name (default: csdc-atl/buffer-cross-001)
  -c COMMIT_HASH      Commit hash (default: 46d270928463db49b317e5ea469a8ac8152f4a13)
  -s S3_BUCKET_NAME   S3 bucket name to upload the model (default: llm-rag)
./model.sh -t <Your Hugging Face Token>
```
2. Upload file to S3 bucket in the S3 bucket you specified <Your S3 bucket/Your S3 bucket prefix> in the previous step or use default bucket

3. Create index in AOS dashboard (Will be deprecated in the future)
Logging into AOS dashboard address in the output of CloudFormation Stack to open Dashboard choose Dev Tools in left side panel, copy and paste the following command to create index
```bash
PUT chatbot-index
{
    "settings" : {
        "index":{
            "number_of_shards" : 1,
            "number_of_replicas" : 0,
            "knn": "true",
            "knn.algo_param.ef_search": 32
        }
    },
    "mappings": {
        "properties": {
            "doc_type" : {
                "type" : "keyword"
            },
            "doc": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart"
            },
            "answer": {
                "type": "text"
            },
            "embedding": {
                "type": "knn_vector",
                "dimension": 768,
                "method": {
                    "name": "hnsw",
                    "space_type": "l2",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 32
                    }
                }            
            }
        }
    }
}
```

4. Test the API connection
Use Postman to test the API connection, the API endpoint is the output of CloudFormation Stack, the API request body is as follows:
```bash
{
  "document_prefix": "<Your S3 bucket prefix>",
  "aos_index": "chatbot-index"
}
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

