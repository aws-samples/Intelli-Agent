## LLM Bot

### Overall Architecture
![image](https://github.com/aws-samples/llm-bot/assets/23544182/acb918e3-3253-4cef-82bb-da65d78b1249)

### ETL Workflow
![image](https://github.com/aws-samples/llm-bot/assets/23544182/f35915ee-69ef-4f15-af83-e0df1d1249be)

### Quick Start

1. Prepare model assets by executing script per model folder
```bash
cd source/model/<cross/embedding/instruct>/model
./model.sh       
Make sure Python installed properly. Usage: ./model.sh -t TOKEN [-m MODEL_NAME] [-c COMMIT_HASH] [-s S3_BUCKET_NAME]
  -t TOKEN            Hugging Face token (required)
  -m MODEL_NAME       Model name (default: csdc-atl/buffer-cross-001)
  -c COMMIT_HASH      Commit hash (default: 46d270928463db49b317e5ea469a8ac8152f4a13)
  -s S3_BUCKET_NAME   S3 bucket name to upload the model (default: llm-rag)
./model.sh -t <Your Hugging Face Token> -s <Your S3 Bucket Name>

cd source/model/etl/code
sh model.sh ./Dockerfile <EtlImageName> <AWS_REGION>
```
The ETL image will be pushed to your ECR repo with the image name you specified when executing the command sh model.sh ./Dockerfile <EtlImageName> <AWS_REGION>, AWS_REGION is like us-east-1, us-west-2, etc.


2. Deploy CDK template (add sudo if you are using Linux), make sure DOCKER is installed properly
```bash
git clone --recursive
git submodule update --init

**optional** step to deploy AI Solution Kit Endpoints (OCR, Semantic Chunk Splitting, Chunk Summary):
cd submodule
npx projen build
npx cdk deploy

cd source/infrastructure
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
npm install
npx cdk deploy --rollback false --parameters S3ModelAssets=<Your S3 Bucket Name> --parameters SubEmail=<Your email address> --parameters OpenSearchIndex=<Your OpenSearch Index Name> --parameters EtlImageName=<Your ETL model name>
```

**Deployment parameters**

| Parameter | Description |
|-|-|
| S3ModelAssets | Your bucket name to store models |
| SubEmail | Your email address to receive notifications |
| OpenSearchIndex | OpenSearch index name to store the knowledge, if the index is not existed, the solution will create one |
| EtlImageName | ETL image name, eg. etl-model, it is set when you executing source/model/etl/code/model.sh script |

You can update us-east-1 to any other available region according to your need. You will get output similar like below:
```
Outputs:
llm-bot-dev.APIEndpointAddress = https://xx.execute-api.us-east-1.amazonaws.com/v1/
llm-bot-dev.CrossModelEndpoint = cross-endpoint
llm-bot-dev.DocumentBucket = llm-bot-documents-xx-us-east-1
llm-bot-dev.EmbeddingModelEndpoint = embedding-endpoint
llm-bot-dev.GlueJobName = PythonShellJobxx
llm-bot-dev.InstructModelEndpoint = instruct-endpoint
llm-bot-dev.OpenSearchEndpoint = vpc-xx.us-east-1.es.amazonaws.com
lm-bot-dev.ProcessedObjectTable = llm-bot-dev-xx
llm-bot-dev.VPC = vpc-xx
Stack ARN:
arn:aws:cloudformation:us-east-1:<Your account id>:stack/llm-bot-dev/xx
```

3. Test the API connection

Use Postman/cURL to test the API connection, the API endpoint is the output of CloudFormation Stack with prefix 'embedding' or 'llm', the sample URL will be like "https://xxxx.execute-api.us-east-1.amazonaws.com/v1/embedding", the API request body is as follows:

**Offline process to pre-process file specified in S3 bucket and prefix, POST https://xxxx.execute-api.us-east-1.amazonaws.com/v1/etl**
```bash
BODY
{
    "s3Bucket": "<Your S3 bucket>", eg. "llm-bot-resource"
    "s3Prefix": "<Your S3 prefix>", eg. "input_samples/"
    "offline": "true",
    "qaEnhance": "false"
}

```


You should see output like this:
```bash
"Step Function triggered, Step Function ARN: arn:aws:states:us-east-1:xxxx:execution:xx-xxx:xx-xx-xx-xx-xx, Input Payload: {\"s3Bucket\": \"<Your S3 bucket>\", \"s3Prefix\": \"<Your S3 prefix>\", \"offline\": \"true\"}"
```

**Then you can query embeddings in AOS, POST https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos**, other operation including index, delete, query are also provided for debugging purpose.
```bash
BODY
{
  "aos_index": "chatbot-index",
  "operation": "query_all",
  "body": ""
}
```

You should see output like this:
```bash
{
  "took": 4,
  "timed_out": false,
  "_shards": {
    "total": 4,
    "successful": 4,
    "skipped": 0,
    "failed": 0
  },
  "hits": {
    "total": {
      "value": 256,
      "relation": "eq"
    },
    "max_score": 1.0,
    "hits": [
      {
        "_index": "chatbot-index",
        "_id": "035e8439-c683-4278-97f3-151f8cd4cdb6",
        "_score": 1.0,
        "_source": {
          "vector_field": [
            -0.03106689453125,
            -0.00798797607421875,
            ...
          ],
          "text": "## 1 Introduction\n\nDeep generative models of all kinds have recently exhibited high quality samples in a wide variety of data modalities. Generative adversarial networks (GANs), autoregressive models, flows, and variational autoencoders (VAEs) have synthesized striking image and audio samples [14; 27; 3; 58; 38; 25; 10; 32; 44; 57; 26; 33; 45], and there have been remarkable advances in energy-based modeling and score matching that have produced images comparable to those of GANs [11; 55].",
          "metadata": {
            "content_type": "paragraph",
            "heading_hierarchy": {
              "1 Introduction": {}
            },
            "figure_list": [],
            "chunk_id": "$2",
            "file_path": "Denoising Diffusion Probabilistic Models.pdf",
            "keywords": [],
            "summary": ""
          }
        }
      },
      ...
    ]
  }
}
```

**Delete initial index in AOS, POST https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos for debugging purpose**
```bash
{
  "aos_index": "chatbot-index",
  "operation": "delete",
  "body": ""
}
```

You should see output like this:
```bash
{
  "acknowledged": true
}
```

**Create other index in AOS, POST https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos for debugging purpose, note the index "chatbot-index" will create by default to use directly**
```bash
{
  "aos_index": "llm-bot-index",
  "operation": "create_index",
  "body": {}
}
```

You should see output like this:
```bash
{
  "acknowledged": true,
  "shards_acknowledged": true,
  "index": "llm-bot-index"
}
```

**Online process to embedding & inject document directly, POST https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos**
```bash
BODY
{
  "aos_index": "llm-bot-index",
  "operation": "embed_document",
  "body": {
    "documents": {
      "page_content": "## Main Title\n This is the main titlebe before such chapter",
      "metadata": {
        "content_type": "paragraph", 
        "heading_hierarchy": "{'Evaluation of LLM Retrievers': {}}", 
        "figure_list": [], 
        "chunk_id": "$9", 
        "file_path": "s3://bucket/file_folder/ec2/user_guide", 
        "keywords": ["ec2", "s3"],
        "summary": "This is summary for such user guide"
      }
    }
  }
}
```

You should see output like this, it will output the document id for the document you just injected:
```bash
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "document_id": [
      "1e70e167-53b4-42d1-9bdb-084c2f2d3282"
    ]
  }
}
```

**Query the embedding with field and value specified, GET https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos**
```bash
{
  "aos_index": "llm-bot-index-01",
  "operation": "query_full_text_match",
  "body": {
      "field": "metadata.file_path",
      "value": "s3://bucket/file_folder/ec2/user_guide",
      "size": 100
  }
}
```

You should see output like this, the metadata.file_path field is matched with the value "s3://bucket/file_folder/ec2/user_guide" and embedding vector is returned with score for relevance possibility:
```bash
{
  "took": 4,
  "timed_out": false,
  "_shards": {
    "total": 5,
    "successful": 5,
    "skipped": 0,
    "failed": 0
  },
  "hits": {
    "total": {
      "value": 1,
      "relation": "eq"
    },
    "max_score": 1.4384104,
    "hits": [
      {
        "_index": "llm-bot-index-01",
        "_id": "94d05a5c-1311-4c16-8f32-67b03526b888",
        "_score": 1.4384104,
        "_source": {
          "vector_field": [
            0.014800798147916794,
            0.04196572303771973,
            ...
          ],
          "text": "### Evaluation of LLM Retrievers\n This is the main body of such chapter",
          "metadata": {
            "content_type": "paragraph",
            "heading_hierarchy": "{'Evaluation of LLM Retrievers': {}}",
            "figure_list": [],
            "chunk_id": "$10",
            "file_path": "s3://bucket/file_folder/ec2/user_guide",
            "keywords": [
              "ec2",
              "s3"
            ],
            "summary": "This is summary for such user guide"
          }
        }
      }
    ]
  }
}
```
**Query the embedding with KNN, GET https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos**
```bash
{
  "aos_index": "llm-bot-index",
  "operation": "query_knn",
  "body": {
      "query": [
            0.014800798147916794,
            0.04196572303771973,
            ...
          ],
      "size": 10
  }
}
```

You should see output like this, the embedding vector is matched with the embedding value and result are returned with score for relevance possibility, we usaually embed our query first to get the float vector and then use the vector to query the AOS:
```bash
{
  "took": 2,
  "timed_out": false,
  "_shards": {
    "total": 5,
    "successful": 5,
    "skipped": 0,
    "failed": 0
  },
  "hits": {
    "total": {
      "value": 2,
      "relation": "eq"
    },
    "max_score": 1.0,
    "hits": [
      {
        "_index": "llm-bot-index",
        "_id": "f57c95cb-ec45-4ea3-8c41-d364897c84ff",
        "_score": 1.0,
        "_source": {
          "vector_field": [
            0.014800798147916794,
            0.04196572303771973,
            ...
          ],
          "text": "### Evaluation of LLM Retrievers\n This is the main body of such chapter",
          "metadata": {
            "content_type": "paragraph",
            "heading_hierarchy": "{'Evaluation of LLM Retrievers': {}}",
            "figure_list": [],
            "chunk_id": "$10",
            "file_path": "s3://bucket/file_folder/ec2/user_guide",
            "keywords": [
              "ec2",
              "s3"
            ],
            "summary": "This is summary for such user guide"
          }
        }
      },
      {
        "_index": "llm-bot-index",
        "_id": "1e70e167-53b4-42d1-9bdb-084c2f2d3282",
        "_score": 0.68924075,
        "_source": {
          "vector_field": [
            -0.02339574135839939,
            0.03578857704997063,
            ...
          ],
          "text": "## Main Title\n This is the main titlebe before such chapter",
          "metadata": {
            "content_type": "paragraph",
            "heading_hierarchy": "{'Evaluation of LLM Retrievers': {}}",
            "figure_list": [],
            "chunk_id": "$9",
            "file_path": "s3://bucket/file_folder/ec2/user_guide",
            "keywords": [
              "ec2",
              "s3"
            ],
            "summary": "This is summary for such user guide"
          }
        }
      }
    ]
  }
}
```
**Query the index for mappings configuration, normally used in debugging model, GET https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos**
```bash
{
  "aos_index": "llm-bot-index",
  "operation": "query_index",
  "body": {
  }
}
```

You should see output like this, the index mapping configuration is returned:
```bash
{
  "llm-bot-index": {
    "mappings": {
      "properties": {
        "metadata": {
          "properties": {
            "chunk_id": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "content_type": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "file_path": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "heading_hierarchy": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "keywords": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "summary": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            }
          }
        },
        "text": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "vector_field": {
          "type": "float"
        }
      }
    }
  }
}
```


There are other operations including 'bulk', 'delete_index', 'delete_document' etc. for debugging purpose, the sample body will be update soon. User will not need to use proxy instance to access the AOS inside VPC, the API gateway with Lambda proxy integration are wrapped to access the AOS directly.


4. [Optional] Launch dashboard to check and debug the ETL & QA process

```bash
cd /source/panel
pip install -r requirements.txt
mv .env_sample .env
# fill .env content accordingly with cdk output
python -m streamlit run app.py --server.runOnSave true --server.port 8088 --browser.gatherUsageStats false --server.fileWatcherType none
```
login with IP/localhost:8088, you should see the dashboard to operate.

5. [Optional] Upload embedding file to S3 bucket created in the previous step, the format is like below:
```bash
aws s3 cp <Your documents> s3://llm-bot-documents-<Your account id>-<region>/<Your S3 bucket prefix>/
```
Now the object created event will trigger the Step function to execute Glue job for online processing.

## Other Sample
Try [Bedrock tuturial](https://github.com/aws-samples/llm-bot/blob/main/sample/bedrock-tuturial.ipynb) quick get though the bedrock model & langchain.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

