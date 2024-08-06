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
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";
import { join } from "path";

import { LambdaLayers } from "../shared/lambda-layers";
import { WebSocketConstruct } from "./websocket-api";
import { Function, Runtime, Code, Architecture, DockerImageFunction, DockerImageCode } from 'aws-cdk-lib/aws-lambda';
import { IAMHelper } from "../shared/iam-helper";
import { JsonSchemaType, JsonSchemaVersion, Model } from "aws-cdk-lib/aws-apigateway";
import { SystemConfig } from "../shared/types";
import { SharedConstruct } from "../shared/shared-construct";
import { ModelConstruct } from "../model/model-construct";
import { KnowledgeBaseStack } from "../knowledge-base/knowledge-base-stack";
import { ChatStack } from "../chat/chat-stack";
import { UserConstruct } from "../user/user-construct";


interface ApiStackProps extends StackProps {
  config: SystemConfig;
  sharedConstruct: SharedConstruct;
  modelConstruct: ModelConstruct;
  knowledgeBaseStack: KnowledgeBaseStack;
  chatStack: ChatStack;
  userConstruct: UserConstruct;
}

export class ApiConstruct extends Construct {
  public apiEndpoint: string = "";
  public documentBucket: string = "";
  public wsEndpoint: string = "";
  public wsEndpointV2: string = "";
  private iamHelper: IAMHelper;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id);

    this.iamHelper = props.sharedConstruct.iamHelper;
    const vpc = props.sharedConstruct.vpcConstruct.vpc;
    const securityGroup = props.sharedConstruct.vpcConstruct.securityGroup;
    const domainEndpoint = props.knowledgeBaseStack.aosConstruct.domainEndpoint;
    const sessionsTableName = props.chatStack.chatTablesConstruct.sessionsTableName;
    const messagesTableName = props.chatStack.chatTablesConstruct.messagesTableName;
    const chatbotTableName = props.sharedConstruct.chatbotTable.tableName;
    const etlEndpointName = props.knowledgeBaseStack.etlEndpoint.endpointName ?? '';
    const resBucketName = props.knowledgeBaseStack.glueResultBucket.bucketName;
    const executionTableName = props.knowledgeBaseStack.executionTable.tableName;
    const etlObjTableName = props.knowledgeBaseStack.etlObjTable.tableName;
    const etlObjIndexName = props.knowledgeBaseStack.etlObjIndexName;

    const chatQueueConstruct = props.chatStack.chatQueueConstruct;
    const sqsStatement = chatQueueConstruct.sqsStatement;
    const messageQueue = chatQueueConstruct.messageQueue;

    const lambdaLayers = new LambdaLayers(this);
    // const apiLambdaExecutorLayer = lambdaLayers.createExecutorLayer();
    const apiLambdaEmbeddingLayer = lambdaLayers.createEmbeddingLayer();
    const apiLambdaOnlineSourceLayer = lambdaLayers.createOnlineSourceLayer();
    const apiLambdaJobSourceLayer = lambdaLayers.createJobSourceLayer();
    const apiLambdaAuthorizerLayer = lambdaLayers.createAuthorizerLayer();

    // S3 bucket for storing documents
    const s3Bucket = new s3.Bucket(this, "llm-bot-documents", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.POST,
            s3.HttpMethods.PUT,
            s3.HttpMethods.DELETE,
          ],
          allowedOrigins: ["*"],
          allowedHeaders: ["*"],
        },
      ],
    });

    const embeddingLambda = new Function(this, "lambdaEmbedding", {
      runtime: Runtime.PYTHON_3_11,
      handler: "main.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/embedding")),
      timeout: Duration.minutes(15),
      memorySize: 4096,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      environment: {
        ETL_MODEL_ENDPOINT: etlEndpointName,
        REGION: Aws.REGION,
        RES_BUCKET: resBucketName,
      },
      layers: [apiLambdaEmbeddingLayer],
    });

    embeddingLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    embeddingLambda.addToRolePolicy(this.iamHelper.s3Statement);
    embeddingLambda.addToRolePolicy(this.iamHelper.endpointStatement);

    const aosLambda = new Function(this, "AOSLambda", {
      runtime: Runtime.PYTHON_3_11,
      handler: "main.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/aos")),
      timeout: Duration.minutes(15),
      memorySize: 1024,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      environment: {
        opensearch_cluster_domain: domainEndpoint,
        embedding_endpoint: props.modelConstruct.embeddingAndRerankerEndPointName,
      },
      layers: [apiLambdaEmbeddingLayer],
    });

    aosLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    aosLambda.addToRolePolicy(this.iamHelper.s3Statement);
    aosLambda.addToRolePolicy(this.iamHelper.endpointStatement);

    const chatHistoryLambda = new Function(this, "ChatHistoryLambda", {
      runtime: Runtime.PYTHON_3_11,
      handler: "rating.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
      environment: {
        SESSIONS_TABLE_NAME: sessionsTableName,
        MESSAGES_TABLE_NAME: messagesTableName,
        SESSIONS_BY_TIMESTAMP_INDEX_NAME: "byTimestamp",
        MESSAGES_BY_SESSION_ID_INDEX_NAME: "bySessionId",
      },
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
    });
    chatHistoryLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);

    const listSessionsLambda = new Function(this, "ListSessionsLambda", {
      runtime: Runtime.PYTHON_3_11,
      handler: "list_sessions.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
      environment: {
        SESSIONS_TABLE_NAME: sessionsTableName,
        SESSIONS_BY_TIMESTAMP_INDEX_NAME: "byTimestamp",
      },
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
    });
    listSessionsLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);

    const listMessagesLambda = new Function(this, "ListMessagesLambda", {
      runtime: Runtime.PYTHON_3_11,
      handler: "list_messages.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
      environment: {
        MESSAGES_TABLE_NAME: messagesTableName,
        MESSAGES_BY_SESSION_ID_INDEX_NAME: "bySessionId",
      },
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
    });
    listMessagesLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);

    // Integration with Step Function to trigger ETL process
    // Lambda function to trigger Step Function
    const sfnLambda = new Function(this, "StepFunctionLambda", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "sfn_handler.handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.seconds(30),
      environment: {
        sfn_arn: props.knowledgeBaseStack.sfnOutput.stateMachineArn,
        EXECUTION_TABLE_NAME: props.knowledgeBaseStack.executionTable.tableName,
        INDEX_TABLE_NAME: props.chatStack.chatTablesConstruct.indexTableName,
        CHATBOT_TABLE_NAME: props.sharedConstruct.chatbotTable.tableName,
        MODEL_TABLE_NAME: props.chatStack.chatTablesConstruct.modelTableName,
        EMBEDDING_ENDPOINT: props.modelConstruct.embeddingAndRerankerEndPointName,
      },
      memorySize: 256,
    });
    sfnLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);

    // Grant lambda function to invoke step function
    props.knowledgeBaseStack.sfnOutput.grantStartExecution(sfnLambda);

    // Uncomment below event bridge if you want to handle the S3 files
    // Add S3 event notification when file uploaded to the bucket
    // s3Bucket.addEventNotification(
    //   s3.EventType.OBJECT_CREATED,
    //   new s3n.LambdaDestination(sfnLambda),
    //   { prefix: "documents/" },
    // );
    // Add S3 event notification when file deleted in the bucket
    // s3Bucket.addEventNotification(
    //   s3.EventType.OBJECT_REMOVED,
    //   new s3n.LambdaDestination(sfnLambda),
    //   { prefix: "documents/" },
    // );
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
    listExecutionLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);

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
    getExecutionLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);

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
    delExecutionLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);

    const uploadDocLambda = new Function(this, "UploadDocument", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "upload_document.lambda_handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.minutes(3),
      memorySize: 512,
      architecture: Architecture.X86_64,
      environment: {
        S3_BUCKET: s3Bucket.bucketName,
      },
    });
    uploadDocLambda.addToRolePolicy(this.iamHelper.s3Statement);

    // Create Lambda Authorizer for WebSocket API
    const customAuthorizerLambda = new Function(this, "CustomAuthorizerLambda", {
      runtime: Runtime.PYTHON_3_11,
      handler: "custom_authorizer.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/authorizer")),
      timeout: Duration.minutes(15),
      memorySize: 1024,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      environment: {
        USER_POOL_ID: props.userConstruct.userPool.userPoolId,
        REGION: Aws.REGION,
        APP_CLIENT_ID: props.userConstruct.oidcClientId,
      },
      layers: [apiLambdaAuthorizerLayer],
    });

    customAuthorizerLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );

    const createChatbotLambda = new Function(this, "CreateChatbot", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "create_chatbot.lambda_handler",
      runtime: Runtime.PYTHON_3_12,
      timeout: Duration.minutes(5),
      memorySize: 512,
      architecture: Architecture.X86_64,
      environment: {
        INDEX_TABLE_NAME: props.chatStack.chatTablesConstruct.indexTableName,
        CHATBOT_TABLE_NAME: props.sharedConstruct.chatbotTable.tableName,
        MODEL_TABLE_NAME: props.chatStack.chatTablesConstruct.modelTableName,
        EMBEDDING_ENDPOINT: props.modelConstruct.embeddingAndRerankerEndPointName,
      },
    });
    createChatbotLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);

    const listChatbotLambda = new Function(this, "ListChatbotLambda", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "list_chatbot.lambda_handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.minutes(15),
      memorySize: 512,
      architecture: Architecture.X86_64,
      environment: {
        USER_POOL_ID: props.userConstruct.userPool.userPoolId,
      },
    });

    listChatbotLambda.addToRolePolicy(this.iamHelper.cognitoStatement);

    // Create Lambda prompt management
    const promptManagementLambda = new Function(this, "PromptManagementLambda", {
      runtime: Runtime.PYTHON_3_12,
      handler: "prompt_management.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/prompt_management")),
      timeout: Duration.minutes(15),
      memorySize: 1024,
      architecture: Architecture.X86_64,
      environment: {
        PROMPT_TABLE_NAME: props.chatStack.chatTablesConstruct.promptTableName,
      },
      layers: [apiLambdaOnlineSourceLayer],
    });

    promptManagementLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    promptManagementLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ],
        effect: iam.Effect.ALLOW,
        resources: [`arn:${Aws.PARTITION}:dynamodb:${Aws.REGION}:${Aws.ACCOUNT_ID}:table/${props.chatStack.chatTablesConstruct.promptTableName}`],
      }),
    );

    // Define the API Gateway
    const api = new apigw.RestApi(this, "Intelli-Agent-RESTful-API", {
      restApiName: "Intelli-Agent-RESTful-API",
      description: "Intelli-Agent RESTful API",
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
        stageName: "prod",
        metricsEnabled: true,
        loggingLevel: apigw.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        tracingEnabled: true,
      },
    });

    const auth = new apigw.RequestAuthorizer(this, 'ApiAuthorizer', {
      handler: customAuthorizerLambda,
      identitySources: [apigw.IdentitySource.header('Authorization')],
    });

    // Define the API Gateway Lambda Integration with proxy and no integration responses
    const lambdaEmbeddingIntegration = new apigw.LambdaIntegration(
      embeddingLambda,
      { proxy: true },
    );

  //   const responseModel = new Model(this, 'ResponseModel', {
  //   restApi: api,
  //   schema: {
  //     schema: JsonSchemaVersion.DRAFT4,
  //     title: 'ResponsePayload',
  //     type: JsonSchemaType.OBJECT,
  //     properties: {
  //       data: { type: JsonSchemaType.STRING },
  //       message: { type: JsonSchemaType.STRING }
  //     },
  //   },
  // });

  // const methodOption = {
  //   authorizer: auth,
  //   methodResponses: [
  //     {
  //       statusCode: '200',
  //       responseModels: {
  //         'application/json': responseModel,
  //       }
  //     },
  //     {
  //       statusCode: '400',
  //       responseModels: {
  //         'application/json': apigw.Model.EMPTY_MODEL,
  //       },
  //     },
  //     {
  //       statusCode: '500',
  //       responseModels: {
  //         'application/json': apigw.Model.EMPTY_MODEL,
  //       },
  //     }
  //   ]
  // };

    // Define the API Gateway Method
    const apiResourceEmbedding = api.root.addResource("extract");
    apiResourceEmbedding.addMethod("POST", lambdaEmbeddingIntegration, this.genMethodOption(api, auth, null),);

    // Define the API Gateway Lambda Integration with proxy and no integration responses
    const lambdaAosIntegration = new apigw.LambdaIntegration(aosLambda, {
      proxy: true,
    });

    // All AOS wrapper should be within such lambda
    const apiResourceAos = api.root.addResource("aos");
    apiResourceAos.addMethod("POST", lambdaAosIntegration, this.genMethodOption(api, auth, null),);
    // Add Get method to query & search index in OpenSearch, such embedding lambda will be updated for online process
    apiResourceAos.addMethod("GET", lambdaAosIntegration, this.genMethodOption(api, auth, null),);

    // Define the API Gateway Lambda Integration with proxy and no integration responses
    const lambdaChatHistoryIntegration = new apigw.LambdaIntegration(chatHistoryLambda, {
      proxy: true,
    });

    const apiResourceDdb = api.root.addResource("chat-history");
    apiResourceDdb.addMethod("POST", lambdaChatHistoryIntegration, this.genMethodOption(api, auth, null),);
    const apiResourceListSessions = apiResourceDdb.addResource("sessions");
    apiResourceListSessions.addMethod("GET", new apigw.LambdaIntegration(listSessionsLambda), this.genMethodOption(api, auth, null),);
    const apiResourceListMessages = apiResourceDdb.addResource("messages");
    apiResourceListMessages.addMethod("GET", new apigw.LambdaIntegration(listMessagesLambda), this.genMethodOption(api, auth, null),);

    const apiResourceChatbot = api.root.addResource("chatbot-management");
    const apiChatbot = apiResourceChatbot.addResource("chatbots");
    apiChatbot.addMethod(
      "POST",
      new apigw.LambdaIntegration(createChatbotLambda),
      this.genMethodOption(api, auth, null),
    );
    apiChatbot.addMethod(
      "GET",
      new apigw.LambdaIntegration(listChatbotLambda),
      this.genMethodOption(api, auth, null),
    );

    const apiResourceStepFunction = api.root.addResource("knowledge-base");
    const apiKBExecution = apiResourceStepFunction.addResource("executions");
    apiKBExecution.addMethod(
      "POST",
      new apigw.LambdaIntegration(sfnLambda),
      {
        ...this.genMethodOption(api, auth, null),
        requestModels: this.genRequestModel(api, {
          "chatbotId": { "type": JsonSchemaType.STRING },
          "indexType": { "type": JsonSchemaType.STRING },
          "offline": { "type": JsonSchemaType.STRING },
          "operationType": { "type": JsonSchemaType.STRING },
          "qaEnhance": { "type": JsonSchemaType.STRING },
          "s3Bucket": { "type": JsonSchemaType.STRING },
          "s3Prefix": { "type": JsonSchemaType.STRING }
        })
      }
    );
    apiKBExecution.addMethod(
      "GET",
      new apigw.LambdaIntegration(listExecutionLambda),
      {...this.genMethodOption(api, auth, {
        Items: {type: JsonSchemaType.ARRAY, items: {
          type: JsonSchemaType.OBJECT,
          properties: {
            s3Prefix: { type: JsonSchemaType.STRING },
            offline: { type: JsonSchemaType.STRING },
            s3Bucket: { type: JsonSchemaType.STRING },
            executionId: { type: JsonSchemaType.STRING },
            executionStatus: { type: JsonSchemaType.STRING },
            qaEnhance: { type: JsonSchemaType.STRING },
            operationType: { type: JsonSchemaType.STRING },
            uiStatus: { type: JsonSchemaType.STRING },
            createTime: { type: JsonSchemaType.STRING }, // Consider using format: 'date-time'
            sfnExecutionId: { type: JsonSchemaType.STRING },
            embeddingModelType: { type: JsonSchemaType.STRING },
            groupName: { type: JsonSchemaType.STRING },
            chatbotId: { type: JsonSchemaType.STRING },
            indexType: { type: JsonSchemaType.STRING },
            indexId: { type: JsonSchemaType.STRING },
          },
          required: ['s3Prefix',
                     'offline',
                     's3Bucket',
                     'executionId',
                     'executionStatus',
                     'qaEnhance',
                     'operationType',
                     'uiStatus',
                     'createTime',
                     'sfnExecutionId',
                     'embeddingModelType',
                     'groupName',
                     'chatbotId',
                     'indexType',
                     'indexId'],
        }
        },
        Count: { type: JsonSchemaType.INTEGER },
        Config: { type: JsonSchemaType.OBJECT,
                  properties: {
                    MaxItems: { type: JsonSchemaType.INTEGER },
                    PageSize: { type: JsonSchemaType.INTEGER },
                    StartingToken: { type: JsonSchemaType.NULL }
                  }
                }
      }),
        requestParameters: {
          'method.request.querystring.max_items': false,
          'method.request.querystring.page_size': false
        },
        // requestValidatorOptions: {
        //   requestValidatorName: `Validator-${Math.random().toString(36).substr(2, 9)}`,
        //   validateRequestParameters: false
        // }
      }
    );
    apiKBExecution.addMethod(
      "DELETE",
      new apigw.LambdaIntegration(delExecutionLambda),
      {
        ...this.genMethodOption(api, auth, {
          data: { type: JsonSchemaType.ARRAY, items: { type: JsonSchemaType.STRING } },
          message: { type: JsonSchemaType.STRING }
        }),
        requestModels: this.genRequestModel(api, {
          "executionId": { "type": JsonSchemaType.ARRAY, "items": { "type": JsonSchemaType.STRING } },
        })
      }
    );

    const apiGetExecutionById = apiKBExecution.addResource("{executionId}");
    apiGetExecutionById.addMethod(
      "GET",
      new apigw.LambdaIntegration(getExecutionLambda),
      {
        ...this.genMethodOption(api, auth, {
          Items: {
            type: JsonSchemaType.ARRAY, items: {
              type: JsonSchemaType.OBJECT,
              properties: {
                s3Prefix: { type: JsonSchemaType.STRING },
                s3Bucket: { type: JsonSchemaType.STRING },
                createTime: { type: JsonSchemaType.STRING }, // Consider using format: 'date-time'
                executionId: { type: JsonSchemaType.STRING },
                s3Path: { type: JsonSchemaType.STRING },
                status: { type: JsonSchemaType.STRING },
              },
              required: ['s3Prefix', 's3Bucket', 'createTime', 's3Path', 'status','executionId'],
            }
          },
          Count: { type: JsonSchemaType.INTEGER }
        }),
        requestParameters: {
          'method.request.path.executionId': true
        },
        // requestModels: this.genRequestModel(api, {
        //   "executionId": { "type": JsonSchemaType.ARRAY, "items": {"type": JsonSchemaType.STRING}},
        // })
      }
    );

    const apiUploadDoc = apiResourceStepFunction.addResource("kb-presigned-url");
    apiUploadDoc.addMethod(
      "POST",
      new apigw.LambdaIntegration(uploadDocLambda),
      {...
        this.genMethodOption(api, auth, {
          data: { type: JsonSchemaType.STRING },
          message: { type: JsonSchemaType.STRING },
          s3Bucket: { type: JsonSchemaType.STRING },
          s3Prefix: { type: JsonSchemaType.STRING }
        }),
        requestModels: this.genRequestModel(api, {
          "content_type": { "type": JsonSchemaType.STRING },
          "file_name": { "type": JsonSchemaType.STRING },

        })
    }
    );

    // Define the API Gateway Lambda Integration to manage prompt
    const lambdaPromptIntegration = new apigw.LambdaIntegration(promptManagementLambda, {
      proxy: true,
    });

    const apiResourcePromptManagement = api.root.addResource("prompt-management");

    const apiResourcePromptManagementModels = apiResourcePromptManagement.addResource("models")
    apiResourcePromptManagementModels.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(api, auth, null));

    const apiResourcePromptManagementScenes = apiResourcePromptManagement.addResource("scenes")
    apiResourcePromptManagementScenes.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(api, auth, null));

    const apiResourcePrompt = apiResourcePromptManagement.addResource("prompts");
    apiResourcePrompt.addMethod("POST", lambdaPromptIntegration, this.genMethodOption(api, auth, null));
    apiResourcePrompt.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(api, auth, null));

    const apiResourcePromptProxy = apiResourcePrompt.addResource("{proxy+}")
    apiResourcePromptProxy.addMethod("DELETE", lambdaPromptIntegration, this.genMethodOption(api, auth, null),);
    apiResourcePromptProxy.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(api, auth, null),);


    // Define the API Gateway Lambda Integration with proxy and no integration responses
    const lambdaExecutorIntegration = new apigw.LambdaIntegration(
      props.chatStack.lambdaOnlineMain,
      { proxy: true },
    );

    // Define the API Gateway Method
    const apiResourceLLM = api.root.addResource("llm");
    apiResourceLLM.addMethod("POST", lambdaExecutorIntegration, this.genMethodOption(api, auth, null));

    const lambdaDispatcher = new Function(this, "lambdaDispatcher", {
      runtime: Runtime.PYTHON_3_11,
      handler: "main.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../../../lambda/dispatcher")),
      timeout: Duration.minutes(15),
      memorySize: 1024,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
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
      sendMessageLambda: props.chatStack.lambdaOnlineMain,
      customAuthorizerLambda: customAuthorizerLambda,
    });
    let wsStage = webSocketApi.websocketApiStage
    this.wsEndpoint = `${wsStage.api.apiEndpoint}/${wsStage.stageName}/`;

    

    this.apiEndpoint = api.url;
    this.documentBucket = s3Bucket.bucketName;
  }

  genMethodOption =(api: apigw.RestApi, auth: apigw.RequestAuthorizer, properties: any)=>{
    let responseModel = apigw.Model.EMPTY_MODEL
    if(properties!==null){
      responseModel = new Model(this, `ResponseModel-${Math.random().toString(36).substr(2, 9)}`, {
        restApi: api,
        schema: {
          schema: JsonSchemaVersion.DRAFT4,
          title: 'ResponsePayload',
          type: JsonSchemaType.OBJECT,
          properties,
        },
      });
    }
    return {
      authorizer: auth,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': responseModel,
          }
        },
        {
          statusCode: '400',
          responseModels: {
            'application/json': apigw.Model.EMPTY_MODEL,
          },
        },
        {
          statusCode: '500',
          responseModels: {
            'application/json': apigw.Model.EMPTY_MODEL,
          },
        }
      ]
    };
  }
  
  genRequestModel = (api: apigw.RestApi, properties: any) =>{
    return {
      'application/json': new Model(this, `PostModel-${Math.random().toString(36).substr(2, 9)}`, {
        restApi: api,
        schema: {
          schema: JsonSchemaVersion.DRAFT4,
          title: 'PostPayload',
          type: JsonSchemaType.OBJECT,
          properties,
          required: Object.keys(properties),
        },
      })
    }
  }
}
