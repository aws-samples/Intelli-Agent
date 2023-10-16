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
./model.sh -t <Your Hugging Face Token> -s <Your S3 Bucket Name>
```

2. Deploy CDK template
```bash
npm install
npx cdk deploy --rollback false --parameters S3ModelAssets=<Your S3 Bucket Name>
```

You will get output similar like below:
```
Outputs:
llm-bot-dev.APIEndpointAddress = https://xx.execute-api.us-east-1.amazonaws.com/v1/
llm-bot-dev.CrossModelEndpoint = cross-endpoint
llm-bot-dev.EmbeddingModelEndpoint = embedding-endpoint
llm-bot-dev.InstructModelEndpoint = instruct-endpoint
llm-bot-dev.OpenSearchDashboard = x.x.x.x:8081/_dashboards
llm-bot-dev.OpenSearchEndpoint = vpc-xx-xx-xx.us-east-1.es.amazonaws.com
llm-bot-dev.VPC = vpc-xx
```

3. Upload embedding file to S3 bucket created in the previous step, the format is like below:
```bash
aws s3 cp dth.txt s3://llm-bot-documents-<your account id>-<region>/<your S3 bucket prefix>/
```
Now the object created event will trigger the Step function to execute Glue job for online processing.

4. Test the API connection

Use Postman/cURL to test the API connection, the API endpoint is the output of CloudFormation Stack with prefix 'embedding' or 'llm', the sample URL will be like "https://xxxx.execute-api.us-east-1.amazonaws.com/v1/embedding", the API request body is as follows:
**offline process to pre-process file specificed in S3 bucket and prefix, POST https://xxxx.execute-api.us-east-1.amazonaws.com/v1/etl**
```bash
BODY
{
    "s3Bucket": "<Your S3 bucket>",
    "s3Prefix": "<Your S3 prefix>",
    "offline": "true"
}
```
You should see output like this:
```bash
"Step Function triggered, Step Function ARN: arn:aws:states:us-east-1:xxxx:execution:xx-xxx:xx-xx-xx-xx-xx, Input Payload: {\"s3Bucket\": \"<Your S3 bucket>\", \"s3Prefix\": \"<Your S3 prefix>\", \"offline\": \"true\"}"
```

**embedding uploaded file into AOS, POST https://xxxx.execute-api.us-east-1.amazonaws.com/v1/embedding**
```bash
BODY
{
  "document_prefix": "<Your S3 bucket prefix>",
  "aos_index": "chatbot-index"
}
```
You should see output like this:
```bash
{
  "created": xx.xx,
  "model": "embedding-endpoint"
}
```

**invoke LLM with context, POST https://xxxx.execute-api.us-east-1.amazonaws.com/v1/llm**
```bash
BODY
{
  "model": "knowledge_qa",
  "messages": [
    {
      "role": "user",
      "content": "给我介绍一下什么是data transfer hub方案？"
    }
  ],
  "temperature": 0.7
}
```
You should see output like this:
```bash
{
  "id": "user_1693493252",
  "object": "chat.completion",
  "created": 1693493252,
  "model": "knowledge_qa",
  "usage": {
    "prompt_tokens": 13,
    "completion_tokens": 7,
    "total_tokens": 20
  },
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "数据传输解决方案（Data Transfer Hub）是一种用于安全、可扩展和可追踪地将数据从不同云服务提供商的对象存储服务（如阿里云 OSS、腾讯 COS、七牛 Kodo等）传输到Amazon S3和Amazon ECR的方案。它提供了一个直观的用户界面，允许客户在界面上创建和管理数据传输任务。通过数据传输解决方案，客户可以实现将数据从其他云服务提供商的对象存储服务传输到Amazon S3，以及在Amazon ECR之间传输容器镜像。该方案采用无服务器架构，按需使用并随用随付。有关更多信息，请参阅实施指南的“成本”部分。",
        "knowledge_sources": [
          "/tmp/tmptezz8py3/csdc/dth.txt"
        ]
      },
      "finish_reason": "stop",
      "index": 0
    }
  ]
}
```

## Other Sample
Try [Bedrock tuturial](https://github.com/aws-samples/llm-bot/blob/main/sample/bedrock-tuturial.ipynb) quick get though the bedrock model & langchain.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

