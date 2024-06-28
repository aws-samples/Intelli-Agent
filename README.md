<h1 align="center">
  Intelli-Agent
</h1>
<h4 align="center">Intelli-Agent: Streamlined Workflow for Building Agent-Based Applications</h4>
<div align="center">
  <h4>
    <a href="https://github.com/aws-samples/Intelli-Agent/commits/main/stargazers"><img src="https://img.shields.io/github/stars/aws-samples/Intelli-Agent.svg?style=plasticr"></a>
    <a href="https://github.com/aws-samples/Intelli-Agent/actions/workflows/pull-request-lint.yml"><img src="https://github.com/aws-samples/Intelli-Agent/actions/workflows/pull-request-lint.yml/badge.svg"></a>
    <a href="https://opensource.org/license/apache-2-0"><img src="https://img.shields.io/badge/License-Apache%202.0-yellow.svg"></a>
  </h4>
</div>

Intelli-Agent offers a streamlined workflow for developing scalable, production-grade agent-based applications, such as conversational chatbots. Key features include:

1. **Enterprise Knowledge Base Creation**: Users can upload private documents in various formats (PDF, DOCX, HTML, CSV, TXT, MD, JSON, JSONL, PNG, JPG, JPEG, WEBP) to construct a personalized knowledge base.

2. **Flexible Mode Options**: Choose from multiple modes (Agent, Chat, RAG) to suit diverse requirements. For instance, the Agent model can interpret user intent, select appropriate tools, and act on iterative results.

3. **Configurable Chat-Based UI**: Our React/Next.js chat interface is user-friendly, making it easy to configure, explore, and customize to meet your specific needs.

4. **Comprehensive RESTful API**: Our full-featured API facilitates easy integration with existing applications, enhancing functionality and user experience.

Intelli-Agent is designed to empower developers to rapidly deploy intelligent, context-aware applications with minimal overhead and maximum efficiency.

## Table of Contents
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Security](#security)
- [License](#license)

## Architecture
Deploying this solution using the default parameters will build the following environment in Amazon Web Services:

![Architecture Image](docs/images/intelli-agent-arch.png)

The execution process is as follows:

1. The solution's front-end website is hosted in an Amazon S3 bucket and distributed via Amazon CloudFront. Authentication is provided by an Amazon Cognito user pool.
2. When users upload documents to the knowledge base through the solution's website, the documents are first uploaded to the Amazon S3 bucket.
3. An Amazon Lambda function is then triggered, which in turn triggers an Amazon Step Functions workflow to process the file. Within Amazon Step Functions, the document is parsed and segmented using an Amazon Glue Job, with intermediate states stored in Amazon DynamoDB and Amazon S3.
4. The Amazon Glue Job vectorizes the segmented text blocks using an Embedding model deployed in an Amazon SageMaker Endpoint and injects them into the vector database Amazon OpenSearch. If the document is in image format (e.g., png, webp) or a pdf with images, the Amazon Glue Job uses Amazon BedRock to interpret the images and convert them to text. Finally, Amazon SNS sends the execution result to the user via email.
5. When users send chat messages through the solution's website, the online module's Amazon API Gateway is triggered. Front-end and back-end communication is achieved via WebSocket API. An Amazon Lambda function integrated with Amazon API Gateway sends the request message to Amazon SQS to prevent message timeout.
6. Messages in Amazon SQS are consumed by the online module's Amazon Lambda, which executes Agent/RAG/Chat logic based on the request parameters and records the chat messages in Amazon DynamoDB. The Amazon Lambda function uses intent recognition to determine the necessary tools and perform the corresponding operations.
7. If the RAG model is selected, the Amazon Lambda function vectorizes the query message using the Embedding model deployed in the Amazon SageMaker Endpoint, retrieves matching knowledge from Amazon OpenSearch, reorders the results, and sends the knowledge to the large language model, which then returns the answer to the front end.
8. During the chat, messages between the user and AI are stored in Amazon DynamoDB. The solution's website retrieves a specific chat record through Amazon API Gateway and Amazon Lambda, allowing the user to continue the conversation based on the content of that chat record.

### Enterprise Knowledge Base Creation
Its data preprocessing module includes format recognition, content extraction, metadata conversion, and semantic segmentation, seamlessly in the background.

![Offline Workflow](docs/images/intelli-agent-kb-etl.png)

When a large number of content injection requests are received, it can automatically scale out by running multiple Amazon Glue jobs concurrently, ensuring these requests are processed in time.

#### Chunk Metadata
Chunk metadata is defined as below shown:
| Name | Description |
| - | - |
|file_path| S3 path to store the file |
|file_type| File type, eg. pdf, html |
|content_type| paragraph: paragraph content |
|current_heading| The heading which the chunk belongs to |
|chunk_id| Unique chunk id |
|heading_hierarchy| Heading hierarchy which is used to locate the chunk in the whole file content |
|title| The heading of current section|
|level| Heading level, eg. H1 is #, H2 is ## in markdown |
|parent| The chunk id of parent section, eg. H2's parent is its H1, H3's parent is its H2 |
|previous| The chunk id of previous paragraph at the same Level |
|child| The chunk ids of sub sections |
|next|The chunk id of next paragraph at the same Level |
|size| The number of the chunks when the paragraph is splitted by a fixed chunk size |

Here is an example

```
{
	"file_path": "s3://example/intelli-agent-user-guide.pdf",
	"file_type": "pdf",
	"content_type": "paragragh",
	"current_heading": "# Intelli-Agent User Guide WebApp",
	"chunk_id": "$1-4659f607-1",
	"heading_hierarchy": {
		"title": "Intelli-Agent User Guide",
		"level": 1,
		"parent": null,
		"previous": null,
		"child": [
			"$2-038759db",
			"$4-68d6e6ca",
			"$6-e9cdcf68"
		],
		"next": null,
		"size": 2
	}
}

```

### Flexible Mode Options

The following graph is generated by online logic which is built 
based on [langgraph](https://langchain-ai.github.io/langgraph/). The first node is **query_preprocess_lambda** which 
handles the chat history. Then the user can choose from three modes: 
chat, rag and agent. The **chat** mode lets you interact directly 
with different LLMs, such as Anthropic Claude 3. 
The **rag** mode will retrieve the relevant contents relating to the
current query and let LLM answer it. The **agent** mode is the most 
complex mode which gives you the possibility to handle complex business 
scenarios. Given the most relevant intention from **intention_detection_lambda** 
and chat history from **query_preprocess_lambda**, **agent_lambda** 
will decide which tools to use and whether the information is enough 
to answer the query. The **parse_tool_calling** node will parse the 
output of **agent_lambda**: 

* **agent_lambda** chooses the wrong tool 
from the perspective of tool format, it will be 
forced to think again through **invalid_tool_calling** edge. 
* **agent_lambda** chooses the valid tool, the tool will be executed 
through **tool_exectue_lambda**. Then, **agent_lambda** will decide 
whether the running results are enough to answer the query.
* There are some cases that **agent_lambda** decides to give the final
response. For cases needing RAG, the **rag_retrieve_lambda** and 
**rag_llm_lambda** will be called. For cases that **agent_lambda** 
needs more information, the **give_rhetorical_question** node will 
be executed. For cases where a constant reply needs to be given, the 
**transfer_reply** and **comfort_reply** will be executed. The 
**give_final_response** means the current results of tool calling 
is enough to answer the query.

```mermaid
flowchart TD
 subgraph ReAct["ReAct"]
    direction TB
        tools_choose_and_results_generation["tools_choose_and_results_generation"]
        results_evaluation{{"results_evaluation"}}
        tools_execution["tools_execution"]
  end
    _start_["_start_"] --> query_preprocess["query_preprocess"]
    query_preprocess == chat mode ==> llm_direct_results_generation["llm_direct_results_generation"]
    query_preprocess == rag mode ==> all_knowledge_retrieve["all_knowledge_retrieve"]
    query_preprocess == agent mode ==> intention_detection["intention_detection"]
    all_knowledge_retrieve --> llm_direct_results_generation & llm_rag_results_generation["llm_rag_results_generation"]
    intention_detection -- similar query found --> matched_query_return["matched_query_return"]
    intention_detection -- intention detected --> tools_choose_and_results_generation
    tools_choose_and_results_generation --> results_evaluation
    results_evaluation -. invalid tool calling .-> tools_choose_and_results_generation
    results_evaluation -. valid tool calling .-> tools_execution
    results_evaluation -. no need tool calling .-> final_results_preparation["final_results_preparation"]
    tools_execution --> tools_choose_and_results_generation
    llm_direct_results_generation --> _end_["_end_"]
    llm_rag_results_generation --> _end_
    matched_query_return --> final_results_preparation
    final_results_preparation --> _end_
     tools_choose_and_results_generation:::process
     results_evaluation:::process
     tools_execution:::process
     query_preprocess:::process
     llm_direct_results_generation:::process
     all_knowledge_retrieve:::process
     intention_detection:::process
     llm_rag_results_generation:::process
     matched_query_return:::process
     final_results_preparation:::process
    style query_preprocess fill:#FF6D00,color:#FFFFFF
    style ReAct fill:#FFCDD2,color:#D50000
```

## Quick Start

[<img src="https://aws-gcr-solutions.s3.cn-north-1.amazonaws.com.cn/intelli-agent/images/Logo.jpg" width="50%">](https://aws-gcr-solutions.s3.cn-north-1.amazonaws.com.cn/intelli-agent/videos/intelli-agent-deployment.mp4 "Intelli-Agent Deployment")

Follow these steps to get started:

1. [Prerequisites](#prerequisites)
2. [Deploy CDK Template](#deploy-cdk-template)

### Prerequisites
Execute following commands to install dependencies such as Python, Git, npm, docker and create a service linked role for Amazon OpenSearch service. You can skip this step if they are already installed.

```bash
wget https://raw.githubusercontent.com/aws-samples/Intelli-Agent/dev/source/script/setup_env.sh
sh setup_env.sh
```

Executing the following command to clone the GitHub repo:
```bash
git clone <this repo>
```


Navigate to the script directory and run the build.sh script. This script requires an S3 bucket name as an argument, which will be used to upload the model. Please make sure the bucket name is located in the same region as the CDK deployment. It also requires ETL image name, ETL image tag, and AWS region as arguments. The ETL image will be pushed to your ECR repo with the image name you specified.

```bash
cd source/script
sh build.sh -b <S3 bucket name> -i <ETL model name> -t <ETL tag name> -r <AWS region>
```

For example:

```bash
sh build.sh -b intelli-agent-model-bucket -i etl-image -t latest -r us-east-1
```


### Deploy CDK Template
Please make sure **docker** is installed and the CDK command is executed in the **same region** of the model files which were uploaded in the previous step. 

Start the deployment by executing the following command:
```bash
cd source/infrastructure
npx cdk deploy --parameters S3ModelAssets=<S3 Bucket Name> --parameters SubEmail=<email address> --parameters EtlImageName=<ETL model name> --parameters ETLTag=<ETL tag name>
```

To deploy the offline process only, you can configure context parameters to skip the online process. 

```bash
npx cdk deploy --parameters S3ModelAssets=<S3 bucket name> --parameters SubEmail=<email address> --parameters EtlImageName=<ETL model name> --parameters ETLTag=<ETL tag name> --context DeploymentMode="OFFLINE_EXTRACT"
```

#### Deployment Parameters
| Parameter | Description |
|-|-|
| S3ModelAssets | Your bucket name to store models |
| SubEmail | Your email address to receive notifications |
| OpenSearchIndex | OpenSearch index name to store the knowledge, if the index does not exist, the solution will create one |
| EtlImageName | ETL image name, eg. etl-model, it is set when you executing source/model/etl/code/model.sh script |
| EtlTag | ETL tag, eg. latest, v1.0, v2.0, the default value is latest, it is set when you executing source/model/etl/code/model.sh script |


#### Optional Context Parameters

| Context | Description |
|---------|-------------|
| DeploymentMode | The mode for deployment. There are three modes: `OFFLINE_EXTRACT`, `OFFLINE_OPENSEARCH`, and `ALL`. Default deployment mode is `ALL`. |


### API Reference
After CDK deployment, you can use a HTTP client such as Postman/cURL to invoke the API by following below API schema. 
- [LLM API Schema](https://github.com/aws-samples/Intelli-Agent/blob/main/docs/LLM_API_SCHEMA.md): send question to LLM and get a response.
- [ETL API Schema](https://github.com/aws-samples/Intelli-Agent/blob/main/docs/ETL_API_SCHEMA.md): upload knowledge to the vector database.
- [AOS API Schema](https://github.com/aws-samples/Intelli-Agent/blob/main/docs/AOS_API_SCHEMA.md): search data in the vector database.


## Testing
For detailed test information, please refer to the [Test Doc](https://github.com/aws-samples/Intelli-Agent/blob/dev/tests/README.md)

## Contribution
See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License
This project is licensed under the Apache-2.0 License.