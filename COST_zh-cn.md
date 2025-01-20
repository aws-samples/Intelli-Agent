# Cost Estimation

To deploy this asset, you will incur charges for the use of Amazon Web Services. The following data is based on the latest version published as of July 2024, deployed in the US East (N. Virginia) region (us-east-1), with a knowledge base built to operate 20 working days per month, consuming up to 4096 tokens per session. The cost estimate is based on the inference model anthropic.claude-3-sonnet.

## Model 1: Full deployment

| **Module**           | **AWS Service**                         | **Required** | **Estimated price per month (USD $)** ｜ **Note** |
|-------------------------|-----------------------------------|
| Deployment Region       | US East (N. Virginia) (`us-east-1`) |
| Latest Version Date     | July 2024                        |
| Operating Days per Month| 20                               |
| Max Tokens per Session  | 4096                             |
| Inference Model         | `anthropic.claude-3-sonnet`      |

| Module               | AWS Service (BOM)   | Required | Configuration                        | Estimated price per month (USD $) | Note                                                                                                                |
|----------------------|---------------------|----------|--------------------------------------|------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| Console              | Amazon CloudFront  | Y        |                                      | 0.00                               | Starting from December 1, 2021, the first 1TB of data transferred to the internet each month is free.               |
| Console              | Amazon S3          | Y        | Standard Storage: 216GB, PUT: 1000, SELECT: 10,000 | 0.38                  | Visiting the UI 10 times/workday generates logs and assets totaling ~216GB/month.                                   |
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