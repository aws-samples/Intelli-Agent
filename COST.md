# Cost Estimation

To deploy this asset, you will incur charges for the use of Amazon Web Services. The following data is based on the latest version published as of July 2024, deployed in the US East (N. Virginia) region (us-east-1), with a knowledge base built to operate 20 working days per month, consuming up to 4096 tokens per session. The cost estimate is based on the inference model anthropic.claude-3-sonnet.

## Model 1: Full deployment

<table>
  <tr>
    <th>Module</th>
    <th>Service</th>
    <th>Required</th>
    <th>price($/Mon)</th>
    <th>Note</th>
  </tr>
  <tr>
    <td rolspan="2">Console</td>
    <td>Amazon CloudFront</td>
    <td>Y</td>
    <td>0.00</td>
    <td>Starting from December 1, 2021, the first 1 TB of data transferred to the internet each month and 10 million HTTP/HTTPS requests from all edge locations will be free. <br><br>Data Transfer < 1TB</td>
  </tr>
  <tr>
    <td>Amazon S3</td>
    <td>Y</td>
    <td>0.38</td>
    <td>Visiting the UI 10 times per workday generates a combined size of 400MB for online and offline logs. The fixed asset size of the UI is 2.1MB. A 100MB PDF, after being split, generates approximately 300MB of S3 files. Adding the fixed assets of the model, which are 20.9GB, the total S3 usage per month is approximately 21.6GB. <br><br>S3 Standard Storage: 21.6GB<br>PUT Request: 1000/Mon.<br>SELECT Request: 10000/Mon.<br>RETURN/SCAN Data: 1GB/Mon. </td>
  </tr>
</table>

| Module               | Service   | Required | price($/Mon) | Note                                                                                                                |
|----------------------|---------------------|----------|------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| Console              | Amazon CloudFront  | Y        | 0.00                               | Starting from December 1, 2021, the first 1 TB of data transferred to the internet each month and 10 million HTTP/HTTPS requests from all edge locations will be free. <br><br>Data Transfer < 1TB|
|                      | Amazon S3          | Y        | 0.38                  | Visiting the UI 10 times per workday generates a combined size of 400MB for online and offline logs. The fixed asset size of the UI is 2.1MB. A 100MB PDF, after being split, generates approximately 300MB of S3 files. Adding the fixed assets of the model, which are 20.9GB, the total S3 usage per month is approximately 21.6GB. <br><br>S3 Standard Storage: 21.6GB<br>PUT Request: 1000/Mon.<br>SELECT Request: 10000/Mon.<br>RETURN/SCAN Data: 1GB/Mon. |
| Console              | Amazon Glue        |          | Glue service type: AWS Glue ETL jobs | 0.41                               | 1 DPU per job x 0.83 hours                                                                                          |
| Core                 | Amazon SageMaker   | N        | Instance type: ml.m5d.4xlarge        | 371.2                             | 38.00 instance hours/month x 0.94 USD + 10GB/month x 0.14 USD                                                       |
| Core                 | AWS Lambda         | Y        | x86_64 architecture, 20,000 requests| 0.00                               | Lambda free tier includes 1M free requests/month and 400,000 GB-seconds of compute time per month.                  |
| Core                 | Amazon DynamoDB    | Y        | Provisioned mode: Read: 6 units, Write: 6 units | 34.92 | 12 tables, 1GB storage/table                                                                                      |
| Core                 | Amazon OpenSearch  | Y        | EBS storage: 300GB, 2-AZ, i3.2xlarge | 1,013.43                          | Total includes instance cost + EBS provisioning                                                                     |
| Core                 | Amazon Cognito     | Y        | SAML or OIDC federation, advanced security features | 69.25 | 100,000 MAUs x 0.08 USD + other costs                                                                              |
| Core                 | Amazon API Gateway | Y        | REST API: 1,000 requests/month       | 0.19                               | WebSocket API: 1,000 connections/day                                                                                |
| Core                 | AWS Step Functions | Y        | 1,000 workflows, 15 state transitions/workflow | 0.28                 |                                                                                                                     |
| Core                 | Amazon ECR         | Y        | 3GB storage                          | 0.30                               | No cross-region data                                                                                                 |
| Core                 | Amazon CloudWatch  | Y        | 10GB/month                           | 5.00                               |                                                                                                                     |
| LLM                  | Amazon Bedrock     | Y        | Input tokens: 10,000K, Output tokens: 10,000K | 8.20                   | Embedding model: 0.20 USD                                                                                           |
| **Total**            |                     |          |                                      | **1,169.52**                       |                                                                                                                     |


## Model 2: Online chat core deployent