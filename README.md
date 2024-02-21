# LLM Bot

LLM Bot is a conversational bot based on Large Language Model (LLM). It includes an online process for user document uploads to an S3 bucket, triggering ETL instantly, and an offline process for batch processing documents in a specified S3 bucket and prefix in parallel.

## Table of Contents
- [Architecture](#architecture)
- [ETL Workflow](#etl-workflow)
- [Quick Start](#quick-start)
- [Deployment Parameters](#deployment-parameters)
- [Testing API Connection](#testing-api-connection)
- [Optional Steps](#optional-steps)
- [Other Samples](#other-samples)
- [Security](#security)
- [License](#license)

## Architecture
![Architecture Image](https://github.com/aws-samples/llm-bot/assets/23544182/f1b52f91-cc20-409b-bb28-8e7810e34543)

## ETL Workflow
The ETL workflow handles documents inside the S3 bucket. It includes document type detection, document handling, and document enhancement. All branches will convert to markdown format to unify the processing.
![ETL Workflow Image](https://github.com/aws-samples/llm-bot/assets/23544182/f35915ee-69ef-4f15-af83-e0df1d1249be)

## Quick Start
Follow these steps to get started:

1. [Prerequisites](#prerequisites)
2. [Prepare Model Assets](#prepare-model-assets)
3. [Deploy CDK Template](#deploy-cdk-template)
4. [Test API Connection](#testing-api-connection)

### Prerequisites
First, you need to clone the repository. You can do this by executing the following command:
```bash
git clone <this repo>
```

Then, you need to install the following prerequisites:
```bash
cd source/infrastructure
npm install
```

### Prepare Model Assets
Execute the script per model folder. Make sure Python is installed properly.

First, navigate to the model directory and run the prepare_model.sh script. This script requires an S3 bucket name as an argument, which will be used to upload the model.

```bash
cd source/model/<rerank/embedding/instruct>/model
./prepare_model.sh -s <Your S3 Bucket Name>
```

Next, navigate to the ETL code directory. Depending on your region, you will use either the Dockerfile or DockerfileCN. The model.sh script requires the Dockerfile, ETL image name, AWS region, and ETL image tag as arguments. The ETL image will be pushed to your ECR repo with the image name you specified.

```bash
cd source/model/etl/code
sh model.sh <./Dockerfile or ./DockerfileCN> <EtlImageName> <AWS_REGION> <EtlImageTag>
```

For example, to prepare ETL model asset in the GCR (Greater China) region, the command is:

```bash
sh model.sh ./DockerfileCN llm-bot-cn cn-northwest-1 latest
```

### Deploy CDK Template
Deploy the CDK template. Make sure DOCKER is installed properly.

```bash
cd source/infrastructure
npx cdk deploy --parameters S3ModelAssets=<Your S3 Bucket Name> --parameters SubEmail=<Your email address> --parameters OpenSearchIndex=<Your OpenSearch Index Name> --parameters EtlImageName=<Your ETL model name> --parameters ETLTag=<Your ETL tag name>
```

To deploy the offline process only, you can configure context parameters to skip the online process. 

```bash
npx cdk deploy --parameters S3ModelAssets=<Your S3 Bucket Name> --parameters SubEmail=<Your email address> --parameters OpenSearchIndex=<Your OpenSearch Index Name> --parameters EtlImageName=<Your ETL model name> --parameters ETLTag=<Your ETL tag name> --context DeploymentMode="OFFLINE_EXTRACT"

```

## Deployment Parameters
| Parameter | Description |
|-|-|
| S3ModelAssets | Your bucket name to store models |
| SubEmail | Your email address to receive notifications |
| OpenSearchIndex | OpenSearch index name to store the knowledge, if the index is not existed, the solution will create one |
| EtlImageName | ETL image name, eg. etl-model, it is set when you executing source/model/etl/code/model.sh script |
| EtlTag | ETL tag, eg. latest, v1.0, v2.0, the default value is latest, it is set when you executing source/model/etl/code/model.sh script |

| Context | Description |
|---------|-------------|
| PipOption | The configuration option for the Python package installer (pip). |
| DeploymentMode | The mode for deployment. There are three modes: `OFFLINE_EXTRACT`, `OFFLINE_OPENSEARCH`, and `ALL`. |


## Testing API Connection
Use Postman/cURL to test the API connection. Please refer to the following API invocation guides for detailed API usage: [AOS API Schema](https://github.com/aws-samples/llm-bot/tree/main/docs/AOS_API_SCHEMA.md), [ETL API Schema](https://github.com/aws-samples/llm-bot/tree/main/docs/ETL_API_SCHEMA.md)

## Optional Steps
1. [Launch Dashboard](#launch-dashboard)
2. [Upload Embedding File](#upload-embedding-file)

### Launch Dashboard
Check and debug the ETL & QA process.

```bash
cd /source/panel
pip install -r requirements.txt
mv .env_sample .env
# fill .env content accordingly with cdk output
python -m streamlit run app.py --server.runOnSave true --server.port 8088 --browser.gatherUsageStats false --server.fileWatcherType none
```

### Upload Embedding File
Upload the embedding file to the S3 bucket created in the previous step. This object created event will trigger the Step function to execute Glue job for online processing.

```bash
aws s3 cp <Your documents> s3://llm-bot-documents-<Your account id>-<region>/<Your S3 bucket prefix>/
```

## Other Samples
Try the [Bedrock tutorial](https://github.com/aws-samples/llm-bot/blob/main/sample/bedrock-tuturial.ipynb) to quickly get through the bedrock model & langchain.

## Security
See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License
This project is licensed under the Apache-2.0 License.