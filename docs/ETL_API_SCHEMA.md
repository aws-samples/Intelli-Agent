## ETL API Invocation Guide

This guide will walk you through the process of invoking the ETL API.

### ETL

<!---
#### Extract Document

To extract a document from a specified S3 bucket and prefix, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/extract`. Use the `need_split` flag to configure if the extracted document needs to be split semantically or kept with the original content.

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

To perform offline (asynchronous) batch processing of documents specified in an S3 bucket and prefix, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/etl`. This process includes extracting, splitting document content, converting to vector representation, and injecting into Amazon Open Search (AOS).

Here is an example of the request body:

```bash
{
    "s3Bucket": "<Your S3 bucket>", // e.g., "llm-bot-resource"
    "s3Prefix": "<Your S3 prefix>", // e.g., "input_samples/"
    "offline": "true",
    "qaEnhance": "false",
    "workspaceId": "<Your Workspace index>" // You can name the workspace index as you like
    "operationType": "create" // You can choose create/update/delete/extract_only
    "documentLanguage": "zh" // You can input the language of the pdf document to increase the accuracy of the extraction
}
```

After making the request, you should see a response similar to this:

```bash
{
    "execution_id": "4dd19f1c-45e1-4d18-9d70-7593f96d001a",
    "step_function_arn": "arn:aws:states:us-east-1:<account_id>:execution

:

ETLStateA5DEA10E-Tgtw66LqdlNH:4dd19f1c-45e1-4d18-9d70-7593f96d001a",
    "input_payload": "{\"s3Bucket\": \"<Your S3 bucket>\", \"s3Prefix\": \"<Your S3 prefix>\", \"offline\": \"true\", \"qaEnhance\": \"false\", \"aosIndex\": \"<Your OpenSearch index>\"}"
}
```

#### Get ETL Status

To get the ETL status by execution id, make a GET request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/etl/execution`.

Here is an example of the request:

```bash
https://xxxx.execute-api.us-east-1.amazonaws.com/v1/etl/execution?executionId=24c9bfdb-f604-4bb2-9495-187b3a38be75
```

After making the request, you should see a response similar to this:

```bash
{
    "Items": [
        {
            "s3Prefix": "api_test/data/document/pdf/sdp_overview.pdf",
            "s3Bucket": "llm-bot-documents-316327952690-ap-northeast-1",
            "createTime": "2024-04-26 07:52:40.658384+00:00",
            "executionId": "df1b08c0-42a4-4ed4-98a7-9ffbd4dbaf86",
            "s3Path": "s3://llm-bot-documents-316327952690-ap-northeast-1/api_test/data/document/pdf/sdp_overview.pdf",
            "status": "SUCCEED"
        }
    ],
    "Count": 1
}
```
