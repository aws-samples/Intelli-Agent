<h1 align="center">
  <a name="logo"><img src="https://llm-bot-with-rag.s3.amazonaws.com/llm-bot-logo.png" alt="LLM Bot logo" width="160"></a>
  <br>
  LLM Bot
</h1>
<h4 align="center">Chatbot with Knowledge ETL and RAG on AWS</h4>
<div align="center">
  <h4>
    <a href="https://github.com/aws-samples/llm-bot/stargazers"><img src="https://img.shields.io/github/stars/aws-samples/llm-bot.svg?style=plasticr"/></a>
    <a href="https://github.com/aws-samples/llm-bot/commits/main"><img src="https://img.shields.io/github/last-commit/aws-samples/llm-bot.svg?style=plasticr"/></a>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-Apache%202.0-yellow.svg"></a>

  </h4>
</div>

LLM Bot provides customers with an end-to-end implementation framework for quickly building Large Language Model (LLM) applications based on RAG technology (such as building private knowledge bases, GenBI, etc.). It utilizes LangChain to implement online processes, making it convenient to customize logic for different scenarios. It supports common enterprise document formats (such as PDF, DOCX, CSV, JSON, etc.) and includes a complete workflow that encompasses document format recognition and content extraction, metadata conversion, semantic segmentation, intent detection, retrieval, and Rerank. It supports multiple embeddings, Rerank, and large language models (such as Claude), helping customers improve accuracy and completeness in content extraction, knowledge retrieval, and model output, while reducing the difficulty of deployment.

## Table of Contents
- [Architecture](#architecture)
- [ETL Workflow](#etl-workflow)
- [Quick Start](#quick-start)
- [Deployment Parameters](#deployment-parameters)
- [API Reference](#api-reference)
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
4. [API Reference](#api-reference)

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

First, navigate to the model directory and run the prepare_model.sh script. This script requires an S3 bucket name as an argument, which will be used to upload the model. Please make sure the bucket name is located in the same region as the CDK deployment.

```bash
cd source/model/
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

Finally, if this is the first time using Amazon OpenSearch in this account, you will need to create a service-linked role for Amazon OpenSearch Service. This role is necessary to allow Amazon OpenSearch Service to manage resources on your behalf.

```bash
aws iam create-service-linked-role --aws-service-name es.amazonaws.com
```

### Deploy CDK Template
Please make sure **docker** is installed and the CDK command is executed in the **same region** of the model files which are uploaded in previous step. 

```bash
cd source/infrastructure
npx cdk deploy --parameters S3ModelAssets=<Your S3 Bucket Name> --parameters SubEmail=<Your email address> --parameters EtlImageName=<Your ETL model name> --parameters ETLTag=<Your ETL tag name>
```

To deploy the offline process only, you can configure context parameters to skip the online process. 

```bash
npx cdk deploy --parameters S3ModelAssets=<Your S3 Bucket Name> --parameters SubEmail=<Your email address> --parameters EtlImageName=<Your ETL model name> --parameters ETLTag=<Your ETL tag name> --context DeploymentMode="OFFLINE_EXTRACT"
```

## Deployment Parameters
| Parameter | Description |
|-|-|
| S3ModelAssets | Your bucket name to store models |
| SubEmail | Your email address to receive notifications |
| OpenSearchIndex | OpenSearch index name to store the knowledge, if the index is not existed, the solution will create one |
| EtlImageName | ETL image name, eg. etl-model, it is set when you executing source/model/etl/code/model.sh script |
| EtlTag | ETL tag, eg. latest, v1.0, v2.0, the default value is latest, it is set when you executing source/model/etl/code/model.sh script |


### Optional Context Parameters

| Context | Description |
|---------|-------------|
| DeploymentMode | The mode for deployment. There are three modes: `OFFLINE_EXTRACT`, `OFFLINE_OPENSEARCH`, and `ALL`. Default deployment mode is `ALL`. |
| LayerPipOption | The configuration option for the Python package installer (pip) for the Lambda layer. Please use it to set PyPi mirror(e.g. -i https://pypi.tuna.tsinghua.edu.cn/simple) when your local development environment is in GCR region. Default LayerPipOption is set to ``. |


## API Reference
After CDK deployment, you can use a HTTP client such as Postman/cURL to invoke the API by following below API schema. 
- [LLM API Schema](https://github.com/aws-samples/llm-bot/tree/main/docs/LLM_API_SCHEMA.md): send question to LLM and get a response.
- [ETL API Schema](https://github.com/aws-samples/llm-bot/tree/main/docs/ETL_API_SCHEMA.md): upload knowledge to vector database.
- [AOS API Schema](https://github.com/aws-samples/llm-bot/tree/main/docs/AOS_API_SCHEMA.md): search data in the vector database.

## Optional Steps
- [Upload Embedding File](#upload-embedding-file)

### Upload Embedding File
Upload the embedding file to the S3 bucket created in the previous step. This object created event will trigger the Step function to execute Glue job for online processing.

```bash
aws s3 cp <Your documents> s3://llm-bot-documents-<Your account id>-<region>/<Your S3 bucket prefix>/
```

## Other Samples
Try the [Bedrock tutorial](https://github.com/aws-samples/llm-bot/blob/main/sample/bedrock-tuturial.ipynb) to quickly get through the bedrock model & langchain.

## Contribution
See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License
This project is licensed under the Apache-2.0 License.