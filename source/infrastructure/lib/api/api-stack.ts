/**********************************************************************************************************************
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                    *
 *                                                                                                                    *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import { Aws, Duration, StackProps } from "aws-cdk-lib";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3n from "aws-cdk-lib/aws-s3-notifications";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import { Construct } from "constructs";
import { join } from "path";

import { BuildConfig } from "../../lib/shared/build-config";
import { Constants } from "../shared/constants";
import { LambdaLayers } from "../shared/lambda-layers";
import { QueueConstruct } from "./api-queue";
import { WebSocketConstruct } from "./websocket-api";
import { Function, Runtime, Code, Architecture, DockerImageFunction, DockerImageCode } from 'aws-cdk-lib/aws-lambda';

interface ApiStackProps extends StackProps {
  apiVpc: ec2.Vpc;
  securityGroup: ec2.SecurityGroup;
  domainEndpoint: string;
  rerankEndPoint: string;
  embeddingEndPoints: string[];
  llmModelId: string;
  instructEndPoint: string;
  sessionsTableName: string;
  messagesTableName: string;
  workspaceTableName: string;
  // Type of StepFunctions
  sfnOutput: sfn.StateMachine;
  openSearchIndex: string;
  openSearchIndexDict: string;
  jobName: string;
  jobQueueArn: string;
  jobDefinitionArn: string;
  etlEndpoint: string;
  resBucketName: string;
  executionTableName: string;
  etlObjTableName: string;
  etlObjIndexName: string;
}

export class ApiConstruct extends Construct {
  public apiEndpoint: string = "";
  public documentBucket: string = "";
  public wsEndpoint: string = "";
  public wsEndpointV2: string = "";
  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id);

    const apiVpc = props.apiVpc;
    const securityGroup = props.securityGroup;
    const domainEndpoint = props.domainEndpoint;
    const aosIndex = props.openSearchIndex;
    const aosIndexDict = props.openSearchIndexDict;
    const sessionsTableName = props.sessionsTableName;
    const messagesTableName = props.messagesTableName;
    const workspaceTableName = props.workspaceTableName;
    const jobQueueArn = props.jobQueueArn;
    const jobDefinitionArn = props.jobDefinitionArn;
    const etlEndpoint = props.etlEndpoint;
    const resBucketName = props.resBucketName;
    const executionTableName = props.executionTableName;
    const etlObjTableName = props.etlObjTableName;
    const etlObjIndexName = props.etlObjIndexName;

    const queueConstruct = new QueueConstruct(this, "LLMQueueStack", {
      namePrefix: Constants.API_QUEUE_NAME,
    });
    const sqsStatement = queueConstruct.sqsStatement;
    const messageQueue = queueConstruct.messageQueue;
    const messageQueueV2 = queueConstruct.messageQueue;

    const lambdaLayers = new LambdaLayers(this);
    // const apiLambdaExecutorLayer = lambdaLayers.createExecutorLayer();
    const apiLambdaEmbeddingLayer = lambdaLayers.createEmbeddingLayer();
    const apiLambdaOnlineUtilsLayer = lambdaLayers.createOnlineUtilsLayer();

    // S3 bucket for storing documents
    const s3Bucket = new s3.Bucket(this, "llm-bot-documents", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    const ddbPolicyDocument = new iam.PolicyStatement({
      actions: ["dynamodb:*"],
      effect: iam.Effect.ALLOW,
      resources: ["*"],
    });

    const embeddingLambda = new Function(this, "lambdaEmbedding", {
      runtime: Runtime.PYTHON_3_11,
      handler: "main.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/embedding")),
      timeout: Duration.minutes(15),
      memorySize: 4096,
      vpc: apiVpc,
      vpcSubnets: {
        subnets: apiVpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      environment: {
        ETL_MODEL_ENDPOINT: etlEndpoint,
        REGION: Aws.REGION,
        RES_BUCKET: resBucketName,
      },
      layers: [apiLambdaEmbeddingLayer],
    });

    embeddingLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "sagemaker:InvokeEndpointAsync",
          "sagemaker:InvokeEndpoint",
          "s3:List*",
          "s3:Put*",
          "s3:Get*",
          "es:*",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );

    const aosLambda = new Function(this, "AOSLambda", {
      runtime: Runtime.PYTHON_3_11,
      handler: "main.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/aos")),
      timeout: Duration.minutes(15),
      memorySize: 1024,
      vpc: apiVpc,
      vpcSubnets: {
        subnets: apiVpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      environment: {
        opensearch_cluster_domain: domainEndpoint,
        embedding_endpoint: props.embeddingEndPoints[0],
      },
      layers: [apiLambdaEmbeddingLayer],
    });

    aosLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "sagemaker:InvokeEndpointAsync",
          "sagemaker:InvokeEndpoint",
          "s3:List*",
          "s3:Put*",
          "s3:Get*",
          "es:*",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );

    const ddbLambda = new Function(this, "DDBLambda", {
      runtime: Runtime.PYTHON_3_11,
      handler: "rating.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
      environment: {
        SESSIONS_TABLE_NAME: sessionsTableName,
        MESSAGES_TABLE_NAME: messagesTableName,
        SESSIONS_BY_USER_ID_INDEX_NAME: "byUserId",
        MESSAGES_BY_SESSION_ID_INDEX_NAME: "bySessionId",
      },
      vpc: apiVpc,
      vpcSubnets: {
        subnets: apiVpc.privateSubnets,
      },
      securityGroups: [props.securityGroup],
    });
    ddbLambda.addToRolePolicy(ddbPolicyDocument);

    // Integration with Step Function to trigger ETL process
    // Lambda function to trigger Step Function
    const sfnLambda = new Function(this, "StepFunctionLambda", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "sfn_handler.handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.seconds(30),
      environment: {
        sfn_arn: props.sfnOutput.stateMachineArn,
        EXECUTION_TABLE: props.executionTableName,
      },
      memorySize: 256,
    });
    sfnLambda.addToRolePolicy(ddbPolicyDocument);

    // Grant lambda function to invoke step function
    props.sfnOutput.grantStartExecution(sfnLambda);

    // Add S3 event notification when file uploaded to the bucket
    s3Bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(sfnLambda),
      { prefix: "documents/" },
    );
    // Add S3 event notification when file deleted in the bucket
    s3Bucket.addEventNotification(
      s3.EventType.OBJECT_REMOVED,
      new s3n.LambdaDestination(sfnLambda),
      { prefix: "documents/" },
    );
    s3Bucket.grantReadWrite(sfnLambda);

    const listExecutionLambda = new Function(this, "ListExecution", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "list_execution.lambda_handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.minutes(15),
      memorySize: 512,
      architecture: Architecture.X86_64,
      environment: {
        EXECUTION_TABLE: executionTableName,
      },
    });
    listExecutionLambda.addToRolePolicy(ddbPolicyDocument);

    const getExecutionLambda = new Function(this, "GetExecution", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "get_execution.lambda_handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.minutes(15),
      memorySize: 512,
      architecture: Architecture.X86_64,
      environment: {
        ETL_OBJECT_TABLE: etlObjTableName,
        ETL_OBJECT_INDEX: etlObjIndexName,
      },
    });
    getExecutionLambda.addToRolePolicy(ddbPolicyDocument);

    const delExecutionLambda = new Function(this, "DeleteExecution", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "delete_execution.lambda_handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.minutes(15),
      memorySize: 512,
      architecture: Architecture.X86_64,
      environment: {
        EXECUTION_TABLE: executionTableName,
      },
    });
    delExecutionLambda.addToRolePolicy(ddbPolicyDocument);

    const batchLambda = new Function(this, "BatchLambda", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/batch")),
      handler: "main.lambda_handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.minutes(15),
      memorySize: 1024,
      vpc: apiVpc,
      vpcSubnets: {
        subnets: apiVpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      environment: {
        document_bucket: s3Bucket.bucketName,
        opensearch_cluster_domain: domainEndpoint,
        embedding_endpoint: props.embeddingEndPoints[0],
        jobName: props.jobName,
        jobQueueArn: props.jobQueueArn,
        jobDefinitionArn: props.jobDefinitionArn,
      },
    });

    batchLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "sagemaker:InvokeEndpointAsync",
          "sagemaker:InvokeEndpoint",
          "s3:List*",
          "s3:Put*",
          "s3:Get*",
          "es:*",
          "batch:*",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );

    // Define the API Gateway
    const api = new apigw.RestApi(this, "llmApi", {
      restApiName: "llmApi",
      description: "This service serves the LLM API.",
      endpointConfiguration: {
        types: [apigw.EndpointType.REGIONAL],
      },
      defaultCorsPreflightOptions: {
        allowHeaders: [
          "Content-Type",
          "X-Amz-Date",
          "Authorization",
          "X-Api-Key",
          "X-Amz-Security-Token",
        ],
        allowMethods: apigw.Cors.ALL_METHODS,
        allowCredentials: true,
        allowOrigins: apigw.Cors.ALL_ORIGINS,
      },
      deployOptions: {
        stageName: "v1",
        metricsEnabled: true,
        loggingLevel: apigw.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        tracingEnabled: true,
      },
    });

    // Define the API Gateway Lambda Integration with proxy and no integration responses
    const lambdaEmbeddingIntegration = new apigw.LambdaIntegration(
      embeddingLambda,
      { proxy: true },
    );

    // Define the API Gateway Method
    const apiResourceEmbedding = api.root.addResource("extract");
    apiResourceEmbedding.addMethod("POST", lambdaEmbeddingIntegration);

    // Define the API Gateway Lambda Integration with proxy and no integration responses
    const lambdaAosIntegration = new apigw.LambdaIntegration(aosLambda, {
      proxy: true,
    });

    // All AOS wrapper should be within such lambda
    const apiResourceAos = api.root.addResource("aos");
    apiResourceAos.addMethod("POST", lambdaAosIntegration);

    // Add Get method to query & search index in OpenSearch, such embedding lambda will be updated for online process
    apiResourceAos.addMethod("GET", lambdaAosIntegration);

    // Define the API Gateway Lambda Integration with proxy and no integration responses
    const lambdaDdbIntegration = new apigw.LambdaIntegration(ddbLambda, {
      proxy: true,
    });

    // All AOS wrapper should be within such lambda
    const apiResourceDdb = api.root.addResource("feedback");
    apiResourceDdb.addMethod("POST", lambdaDdbIntegration);

    const apiResourceStepFunction = api.root.addResource("etl");
    apiResourceStepFunction.addMethod(
      "POST",
      new apigw.LambdaIntegration(sfnLambda),
    );

    const apiGetExecution = apiResourceStepFunction.addResource("execution");
    apiGetExecution.addMethod(
      "GET",
      new apigw.LambdaIntegration(getExecutionLambda),
    );

    const apiListExecution = apiResourceStepFunction.addResource("list-execution");
    apiListExecution.addMethod(
      "GET",
      new apigw.LambdaIntegration(listExecutionLambda),
    );

    const apiDelExecution = apiResourceStepFunction.addResource("delete-execution");
    apiDelExecution.addMethod(
      "POST",
      new apigw.LambdaIntegration(delExecutionLambda),
    );

    // Define the API Gateway Lambda Integration to invoke Batch job
    const lambdaBatchIntegration = new apigw.LambdaIntegration(batchLambda, {
      proxy: true,
    });

    // Define the API Gateway Method
    const apiResourceBatch = api.root.addResource("batch");
    apiResourceBatch.addMethod("POST", lambdaBatchIntegration);

    if (BuildConfig.DEPLOYMENT_MODE === "ALL") {
      const lambdaExecutor = new DockerImageFunction(this, "lambdaExecutor", {
        code: DockerImageCode.fromImageAsset(
          join(__dirname, "../../../lambda/executor"),
        ),
        timeout: Duration.minutes(15),
        memorySize: 10240,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        environment: {
          aos_endpoint: domainEndpoint,
          llm_model_endpoint_name: props.instructEndPoint,
          llm_model_id: props.llmModelId,
          embedding_endpoint: props.embeddingEndPoints[0],
          zh_embedding_endpoint: props.embeddingEndPoints[0],
          en_embedding_endpoint: props.embeddingEndPoints[0],
          intent_recognition_embedding_endpoint: props.embeddingEndPoints[0],
          rerank_endpoint: props.rerankEndPoint,
          aos_index: aosIndex,
          aos_index_dict: aosIndexDict,
          sessions_table_name: sessionsTableName,
          messages_table_name: messagesTableName,
          workspace_table: workspaceTableName,
        },
      });

      lambdaExecutor.addToRolePolicy(
        new iam.PolicyStatement({
          // principals: [new iam.AnyPrincipal()],
          actions: [
            "sagemaker:InvokeEndpointAsync",
            "sagemaker:InvokeEndpoint",
            "s3:List*",
            "s3:Put*",
            "s3:Get*",
            "es:*",
            "dynamodb:*",
            "secretsmanager:GetSecretValue",
            "translate:*",
            "bedrock:*",
          ],
          effect: iam.Effect.ALLOW,
          resources: ["*"],
        }),
      );
      lambdaExecutor.addToRolePolicy(sqsStatement);
      lambdaExecutor.addEventSource(
        new lambdaEventSources.SqsEventSource(messageQueue, { batchSize: 1 }),
      );

      // Define the API Gateway Lambda Integration with proxy and no integration responses
      const lambdaExecutorIntegration = new apigw.LambdaIntegration(
        lambdaExecutor,
        { proxy: true },
      );

      // Define the API Gateway Method
      const apiResourceLLM = api.root.addResource("llm");
      apiResourceLLM.addMethod("POST", lambdaExecutorIntegration);

      const lambdaDispatcher = new Function(this, "lambdaDispatcher", {
        runtime: Runtime.PYTHON_3_11,
        handler: "main.lambda_handler",
        code: Code.fromAsset(join(__dirname, "../../../lambda/dispatcher")),
        timeout: Duration.minutes(15),
        memorySize: 1024,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        environment: {
          SQS_QUEUE_URL: messageQueue.queueUrl,
        },
      });
      lambdaDispatcher.addToRolePolicy(sqsStatement);

      const webSocketApi = new WebSocketConstruct(this, "WebSocketApi", {
        dispatcherLambda: lambdaDispatcher,
        sendMessageLambda: lambdaExecutor,
      });
      let wsStage = webSocketApi.websocketApiStage
      this.wsEndpoint = `${wsStage.api.apiEndpoint}/${wsStage.stageName}/`;

      const lambdaOnlineMain = new Function(this, "lambdaOnlineMain", {
        runtime: Runtime.PYTHON_3_12,
        handler: "main.lambda_handler",
        code: Code.fromAsset(
          join(__dirname, "../../../lambda/online/lambda_main"),
        ),
        timeout: Duration.minutes(15),
        memorySize: 4096,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        layers: [apiLambdaOnlineUtilsLayer],
        // environment: {
        //   aos_endpoint: domainEndpoint,
        //   llm_model_endpoint_name: props.instructEndPoint,
        //   llm_model_id: props.llmModelId,
        //   embedding_endpoint: props.embeddingEndPoints[0],
        //   zh_embedding_endpoint: props.embeddingEndPoints[0],
        //   en_embedding_endpoint: props.embeddingEndPoints[0],
        //   intent_recognition_embedding_endpoint: props.embeddingEndPoints[0],
        //   rerank_endpoint: props.rerankEndPoint,
        //   aos_index: aosIndex,
        //   aos_index_dict: aosIndexDict,
        //   sessions_table_name: sessionsTableName,
        //   messages_table_name: messagesTableName,
        //   workspace_table: workspaceTableName,
        // },
      });

      lambdaOnlineMain.addToRolePolicy(
        new iam.PolicyStatement({
          // principals: [new iam.AnyPrincipal()],
          actions: [
            "sagemaker:InvokeEndpointAsync",
            "sagemaker:InvokeEndpoint",
            "s3:List*",
            "s3:Put*",
            "s3:Get*",
            "es:*",
            "dynamodb:*",
            "secretsmanager:GetSecretValue",
            "translate:*",
            "bedrock:*",
            "lambda:InvokeFunction",
          ],
          effect: iam.Effect.ALLOW,
          resources: ["*"],
        }),
      );
      lambdaOnlineMain.addToRolePolicy(sqsStatement);
      lambdaOnlineMain.addEventSource(
        new lambdaEventSources.SqsEventSource(messageQueue, { batchSize: 1 }),
      );

      const lambdaOnlineQueryPreprocess = new Function(this, "lambdaOnlineQueryPreprocess", {
        runtime: Runtime.PYTHON_3_12,
        handler: "main.lambda_handler",
        functionName: "Online_Query_Preprocess",
        code: Code.fromAsset(
          join(__dirname, "../../../lambda/online/lambda_query_preprocess"),
        ),
        timeout: Duration.minutes(15),
        memorySize: 4096,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        layers: [apiLambdaOnlineUtilsLayer],
      });

      const lambdaOnlineIntentionDetection = new Function(this, "lambdaOnlineIntentionDetection", {
        runtime: Runtime.PYTHON_3_12,
        handler: "main.lambda_handler",
        functionName: "Online_Intention_Detection",
        code: Code.fromAsset(
          join(__dirname, "../../../lambda/online/lambda_intention_detection"),
        ),
        timeout: Duration.minutes(15),
        memorySize: 4096,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        layers: [apiLambdaOnlineUtilsLayer],
      });

      const lambdaOnlineAgent = new Function(this, "lambdaOnlineAgent", {
        runtime: Runtime.PYTHON_3_12,
        handler: "main.lambda_handler",
        functionName: "Online_Agent",
        code: Code.fromAsset(
          join(__dirname, "../../../lambda/online/lambda_agent"),
        ),
        timeout: Duration.minutes(15),
        memorySize: 4096,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        layers: [apiLambdaOnlineUtilsLayer],
      });

      const lambdaOnlineLLMGenerate = new Function(this, "lambdaOnlineLLMGenerate", {
        runtime: Runtime.PYTHON_3_12,
        handler: "main.lambda_handler",
        functionName: "Online_LLM_Generate",
        code: Code.fromAsset(
          join(__dirname, "../../../lambda/online/lambda_llm_generate"),
        ),
        timeout: Duration.minutes(15),
        memorySize: 4096,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        layers: [apiLambdaOnlineUtilsLayer],
      });

      const lambdaOnlineFunctionKnowledgeBase = new Function(this, "lambdaOnlineKnowledgeBase", {
        runtime: Runtime.PYTHON_3_12,
        handler: "main.lambda_handler",
        functionName: "Online_Function_Knowledge_Base",
        code: Code.fromAsset(
          join(__dirname, "../../../lambda/online/functions/lambda_knowledge_base"),
        ),
        timeout: Duration.minutes(15),
        memorySize: 4096,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        layers: [apiLambdaOnlineUtilsLayer],
      });

      const lambdaOnlineFunctionWebSearch = new Function(this, "lambdaOnlineWebSearch", {
        runtime: Runtime.PYTHON_3_12,
        handler: "main.lambda_handler",
        functionName: "Online_Function_Web_Search",
        code: Code.fromAsset(
          join(__dirname, "../../../lambda/online/functions/lambda_web_search"),
        ),
        timeout: Duration.minutes(15),
        memorySize: 4096,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        layers: [apiLambdaOnlineUtilsLayer],
      });

      lambdaOnlineQueryPreprocess.grantInvoke(lambdaOnlineMain);
      lambdaOnlineIntentionDetection.grantInvoke(lambdaOnlineMain);
      lambdaOnlineAgent.grantInvoke(lambdaOnlineMain);
      lambdaOnlineLLMGenerate.grantInvoke(lambdaOnlineMain);
      lambdaOnlineFunctionKnowledgeBase.grantInvoke(lambdaOnlineMain);
      lambdaOnlineFunctionWebSearch.grantInvoke(lambdaOnlineMain);

      // Define the API Gateway Lambda Integration with proxy and no integration responses
      const lambdaExecutorIntegrationV2 = new apigw.LambdaIntegration(
        lambdaOnlineMain,
        { proxy: true },
      );

      // Define the API Gateway Method
      const apiResourceLLMV2 = api.root.addResource("llmv2");
      apiResourceLLMV2.addMethod("POST", lambdaExecutorIntegrationV2);

      const lambdaDispatcherV2 = new Function(this, "lambdaDispatcherV2", {
        runtime: Runtime.PYTHON_3_11,
        handler: "main.lambda_handler",
        code: Code.fromAsset(join(__dirname, "../../../lambda/dispatcher")),
        timeout: Duration.minutes(15),
        memorySize: 1024,
        vpc: apiVpc,
        vpcSubnets: {
          subnets: apiVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        architecture: Architecture.X86_64,
        environment: {
          SQS_QUEUE_URL: messageQueueV2.queueUrl,
        },
      });
      lambdaDispatcherV2.addToRolePolicy(sqsStatement);

      const webSocketApiV2 = new WebSocketConstruct(this, "WebSocketApiV2", {
        dispatcherLambda: lambdaDispatcherV2,
        sendMessageLambda: lambdaOnlineMain,
      });
      let wsStageV2 = webSocketApiV2.websocketApiStage
      this.wsEndpointV2 = `${wsStageV2.api.apiEndpoint}/${wsStageV2.stageName}/`;
 
    }

    this.apiEndpoint = api.url;
    this.documentBucket = s3Bucket.bucketName;
  }
}
