## Knowledge Base API Invocation Guide

This guide will walk you through the process of invoking the ETL API.

### ETL

<!---
#### Extract Document

To extract a document from a specified S3 bucket and prefix, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/prod/extract`. Use the `need_split` flag to configure if the extracted document needs to be split semantically or kept with the original content.

Here is an example of the request body:

```bash
{
    "s3_bucket": "<Your S3 bucket>", // e.g., "llm-bot-resource"
    "s3_prefix": "<Your S3 prefix>", // e.g., "input_samples/"
    "need_split": true
}
```
-->

#### Offline Batch Processing

To perform offline (asynchronous) batch processing of documents specified in an S3 bucket and prefix, make a **POST** request to `https://<host_name_prefix>.amazonaws.com/prod/knowledge-base/executions`. This process includes extracting, splitting document content, converting to vector representation, and injecting into Amazon Open Search (AOS).

Here is an example of the request body:

```bash
{
    "s3Bucket": "<Your S3 bucket>", // e.g., "llm-bot-resource"
    "s3Prefix": "<Your S3 prefix>", // e.g., "input_samples/demo.pdf"
    "chatbotId": "<Your chatbot ID>", // Chatbot id is the Cognito group name in lower case, e.g. admin
    "indexId": "<Your index name>", // AOS index name such as qq-retail, the document will be injected into this index
    "indexType": "qd" // You can choose qq/qd, qq is used for question-answer/QA pairs, qd is for injecting documents into the knowledge base
    "tag": "retail", // When you have multiple indexes with same index type, for example, two qd indexes, each index store different type of documents. Tags are used to distinguish between them, so keep it unique
    "offline": "true",
    "qaEnhance": "false",
    "operationType": "create" // You can choose create/update/delete/extract_only, use create if this is the first time to inject the document
}
```

After making the request, you should see a response similar to this:

```bash
{
    "execution_id": "4dd19f1c-45e1-4d18-9d70-7593f96d001a",
    "step_function_arn": "arn:aws:states:<region>:<account_id>:execution

:

ETLStateA5DEA10E-Tgtw66LqdlNH:4dd19f1c-45e1-4d18-9d70-7593f96d001a",
    "input_payload": "{<your_input_payload>}"
}
```

#### Get ETL Status

To get the ETL status by execution id, make a **GET** request to `https://<host_name_prefix>.amazonaws.com/prod/knowledge-base/executions/{executionId}`.

Here is an example of the request:

```bash
https://xxxx.execute-api.us-east-1.amazonaws.com/prod/knowledge-base/executions/24c9bfdb-f604-4bb2-9495-187b3a38be75
```

After making the request, you should see a response similar to this:

```bash
{
    "Items": [
        {
            "s3Prefix": "<folder_name>/demo.pdf",
            "s3Bucket": "<bucket_name>",
            "createTime": "2024-04-26 07:52:40.658384+00:00",
            "executionId": "df1b08c0-42a4-4ed4-98a7-9ffbd4dbaf86",
            "s3Path": "s3://<bucket_name>/<folder_name>/demo.pdf",
            "status": "SUCCEED"
        }
    ],
    "Count": 1
}
```
