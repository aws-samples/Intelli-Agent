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

import { Aws, Duration, Size, StackProps } from "aws-cdk-lib";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Function, Runtime, Code, Architecture } from 'aws-cdk-lib/aws-lambda';
import { JsonSchemaType, JsonSchemaVersion, Model } from "aws-cdk-lib/aws-apigateway";
import { Construct } from "constructs";
import { join } from "path";
import * as S3Deployment from 'aws-cdk-lib/aws-s3-deployment';
import { LambdaLayers } from "../shared/lambda-layers";
import { WebSocketConstruct } from "./websocket-api";
import { IAMHelper } from "../shared/iam-helper";
import { SystemConfig } from "../shared/types";
import { SharedConstructOutputs } from "../shared/shared-construct";
import { ModelConstructOutputs } from "../model/model-construct";
import { KnowledgeBaseStackOutputs } from "../knowledge-base/knowledge-base-stack";
import { ChatStackOutputs } from "../chat/chat-stack";
import { UserConstructOutputs } from "../user/user-construct";
import { LambdaFunction } from "../shared/lambda-helper";
import { Constants } from "../shared/constants";

interface ApiStackProps extends StackProps {
  config: SystemConfig;
  sharedConstructOutputs: SharedConstructOutputs;
  modelConstructOutputs: ModelConstructOutputs;
  knowledgeBaseStackOutputs: KnowledgeBaseStackOutputs;
  chatStackOutputs: ChatStackOutputs;
  userConstructOutputs: UserConstructOutputs;
}

export class ApiConstruct extends Construct {
  public apiEndpoint: string = "";
  public documentBucket: string = "";
  public wsEndpoint: string = "";
  public wsEndpointV2: string = "";
  private iamHelper: IAMHelper;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id);

    this.iamHelper = props.sharedConstructOutputs.iamHelper;
    const vpc = props.sharedConstructOutputs.vpc;
    const securityGroups = props.sharedConstructOutputs.securityGroups;
    const domainEndpoint = props.knowledgeBaseStackOutputs.aosDomainEndpoint;
    const sessionsTableName = props.chatStackOutputs.sessionsTableName;
    const messagesTableName = props.chatStackOutputs.messagesTableName;
    const resBucketName = props.sharedConstructOutputs.resultBucket.bucketName;
    const executionTableName = props.knowledgeBaseStackOutputs.executionTableName;
    const etlObjTableName = props.knowledgeBaseStackOutputs.etlObjTableName;
    const etlObjIndexName = props.knowledgeBaseStackOutputs.etlObjIndexName;

    const sqsStatement = props.chatStackOutputs.sqsStatement;
    const messageQueue = props.chatStackOutputs.messageQueue;

    const lambdaLayers = new LambdaLayers(this);
    // const apiLambdaExecutorLayer = lambdaLayers.createExecutorLayer();
    const apiLambdaEmbeddingLayer = lambdaLayers.createEmbeddingLayer();
    const apiLambdaOnlineSourceLayer = lambdaLayers.createOnlineSourceLayer();
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

    new S3Deployment.BucketDeployment(this, 'IntentionCorpusTemplate', {
      memoryLimit: 512,
      ephemeralStorageSize: Size.mebibytes(512),
      sources: [S3Deployment.Source.asset('lib/api/asset')],
      destinationBucket: s3Bucket,
      destinationKeyPrefix: 'templates',
    });

    // Define the API Gateway
    const api = new apigw.RestApi(this, `${Constants.SOLUTION_SHORT_NAME.toLowerCase()}-api`, {
      description: `${Constants.SOLUTION_NAME} - Core API`,
      endpointConfiguration: {
        types: [apigw.EndpointType.REGIONAL],
      },
      defaultCorsPreflightOptions: {
        allowHeaders: [
          "Content-Type",
          "X-Amz-Date",
          "Authorization",
          "X-Api-Key",
          "Author",
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

    const customAuthorizerLambda = new LambdaFunction(this, "CustomAuthorizerLambda", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/authorizer")),
      handler: "custom_authorizer.lambda_handler",
      environment: {
        USER_POOL_ID: props.userConstructOutputs.userPool.userPoolId,
        REGION: Aws.REGION,
        APP_CLIENT_ID: props.userConstructOutputs.oidcClientId,
      },
      layers: [apiLambdaAuthorizerLayer],
      statements: [props.sharedConstructOutputs.iamHelper.logStatement],
    });


    const auth = new apigw.RequestAuthorizer(this, 'ApiAuthorizer', {
      handler: customAuthorizerLambda.function,
      identitySources: [apigw.IdentitySource.header('Authorization')],
    });

    if (props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled) {
      const embeddingLambda = new LambdaFunction(this, "lambdaEmbedding", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/embedding")),
        vpc: vpc,
        securityGroups: securityGroups,
        environment: {
          ETL_MODEL_ENDPOINT: props.modelConstructOutputs.defaultKnowledgeBaseModelName,
          REGION: Aws.REGION,
          RES_BUCKET: resBucketName,
        },
        layers: [apiLambdaEmbeddingLayer],
        statements: [
          this.iamHelper.esStatement,
          this.iamHelper.s3Statement,
          this.iamHelper.endpointStatement,
        ],
      });
  
      const aosLambda = new LambdaFunction(this, "AOSLambda", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/aos")),
        vpc: vpc,
        securityGroups: securityGroups,
        environment: {
          opensearch_cluster_domain: domainEndpoint,
          embedding_endpoint: props.modelConstructOutputs.defaultEmbeddingModelName,
        },
        layers: [apiLambdaEmbeddingLayer],
        statements: [
          this.iamHelper.esStatement,
          this.iamHelper.s3Statement,
          this.iamHelper.endpointStatement,
        ],
      });

      const listExecutionLambda = new LambdaFunction(this, "ListExecution", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
        handler: "list_execution.lambda_handler",
        environment: {
          EXECUTION_TABLE: executionTableName,
        },
        statements: [this.iamHelper.dynamodbStatement],
      });
  
      const getExecutionLambda = new LambdaFunction(this, "GetExecution", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
        handler: "get_execution.lambda_handler",
        environment: {
          ETL_OBJECT_TABLE: etlObjTableName,
          ETL_OBJECT_INDEX: etlObjIndexName,
        },
        statements: [this.iamHelper.dynamodbStatement],
      });
  
      const delExecutionLambda = new LambdaFunction(this, "DeleteExecution", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
        handler: "delete_execution.lambda_handler",
        environment: {
          EXECUTION_TABLE: executionTableName,
        },
        statements: [this.iamHelper.dynamodbStatement],
      });

      const uploadDocLambda = new LambdaFunction(this, "UploadDocument", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
        handler: "upload_document.lambda_handler",
        environment: {
          S3_BUCKET: s3Bucket.bucketName,
        },
        statements: [this.iamHelper.s3Statement],
      });

      // Define the API Gateway Lambda Integration with proxy and no integration responses
      const lambdaEmbeddingIntegration = new apigw.LambdaIntegration(
        embeddingLambda.function,
        { proxy: true },
      );

      // Define the API Gateway Method
      const apiResourceEmbedding = api.root.addResource("extract");
      apiResourceEmbedding.addMethod("POST", lambdaEmbeddingIntegration, this.genMethodOption(api, auth, null),);

      // Define the API Gateway Lambda Integration with proxy and no integration responses
      const lambdaAosIntegration = new apigw.LambdaIntegration(aosLambda.function, {
        proxy: true,
      });

      // All AOS wrapper should be within such lambda
      const apiResourceAos = api.root.addResource("aos");
      apiResourceAos.addMethod("POST", lambdaAosIntegration, this.genMethodOption(api, auth, null),);
      // Add Get method to query & search index in OpenSearch, such embedding lambda will be updated for online process
      apiResourceAos.addMethod("GET", lambdaAosIntegration, this.genMethodOption(api, auth, null),);

      const apiResourceStepFunction = api.root.addResource("knowledge-base");
      const apiKBExecution = apiResourceStepFunction.addResource("executions");
      if ( props.knowledgeBaseStackOutputs.sfnOutput !== undefined) {
        // Integration with Step Function to trigger ETL process
        // Lambda function to trigger Step Function
        const sfnLambda = new LambdaFunction(this, "StepFunctionLambda", {
          code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
          handler: "sfn_handler.handler",
          environment: {
            sfn_arn: props.knowledgeBaseStackOutputs.sfnOutput.stateMachineArn,
            EXECUTION_TABLE_NAME: props.knowledgeBaseStackOutputs.executionTableName,
            INDEX_TABLE_NAME: props.sharedConstructOutputs.indexTable.tableName,
            CHATBOT_TABLE_NAME: props.sharedConstructOutputs.chatbotTable.tableName,
            MODEL_TABLE_NAME: props.sharedConstructOutputs.modelTable.tableName,
            EMBEDDING_ENDPOINT: props.modelConstructOutputs.defaultEmbeddingModelName,
          },
          statements: [this.iamHelper.dynamodbStatement],
        });
        // Grant lambda function to invoke step function
        props.knowledgeBaseStackOutputs.sfnOutput.grantStartExecution(sfnLambda.function);
        s3Bucket.grantReadWrite(sfnLambda.function);

        apiKBExecution.addMethod(
          "POST",
          new apigw.LambdaIntegration(sfnLambda.function),
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
      }
      apiKBExecution.addMethod(
        "GET",
        new apigw.LambdaIntegration(listExecutionLambda.function),
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
          }
        }
      );
      apiKBExecution.addMethod(
        "DELETE",
        new apigw.LambdaIntegration(delExecutionLambda.function),
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
        new apigw.LambdaIntegration(getExecutionLambda.function),
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
        new apigw.LambdaIntegration(uploadDocLambda.function),
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
    }

    if (props.config.chat.enabled) {
      const chatHistoryLambda = new LambdaFunction(this, "ChatHistoryLambda", {
        handler: "rating.lambda_handler",
        code: Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
        environment: {
          SESSIONS_TABLE_NAME: sessionsTableName,
          MESSAGES_TABLE_NAME: messagesTableName,
          SESSIONS_BY_TIMESTAMP_INDEX_NAME: "byTimestamp",
          MESSAGES_BY_SESSION_ID_INDEX_NAME: "bySessionId",
        },
        statements: [this.iamHelper.dynamodbStatement],
      });
  
      const listSessionsLambda = new LambdaFunction(this, "ListSessionsLambda", {
        handler: "list_sessions.lambda_handler",
        code: Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
        environment: {
          SESSIONS_TABLE_NAME: sessionsTableName,
          SESSIONS_BY_TIMESTAMP_INDEX_NAME: "byTimestamp",
        },
        statements: [this.iamHelper.dynamodbStatement],
      });
  
      const listMessagesLambda = new LambdaFunction(this, "ListMessagesLambda", {
        handler: "list_messages.lambda_handler",
        code: Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
        environment: {
          MESSAGES_TABLE_NAME: messagesTableName,
          MESSAGES_BY_SESSION_ID_INDEX_NAME: "bySessionId",
        },
        statements: [this.iamHelper.dynamodbStatement],
      });
  
      const promptManagementLambda = new LambdaFunction(this, "PromptManagementLambda", {
        runtime: Runtime.PYTHON_3_12,
        code: Code.fromAsset(join(__dirname, "../../../lambda/prompt_management")),
        handler: "prompt_management.lambda_handler",
        environment: {
          PROMPT_TABLE_NAME: props.chatStackOutputs.promptTableName,
        },
        layers: [apiLambdaOnlineSourceLayer],
        statements: [this.iamHelper.dynamodbStatement,
                      this.iamHelper.logStatement],
      });


      const intentionLambda = new LambdaFunction(this, "IntentionLambda", {
        runtime: Runtime.PYTHON_3_12,
        code: Code.fromAsset(join(__dirname, "../../../lambda/intention")),
        handler: "intention.lambda_handler",
        vpc: vpc,
        securityGroups: securityGroups,
        environment: {
          INTENTION_TABLE_NAME: props.chatStackOutputs.intentionTableName,
          INDEX_TABLE_NAME: props.sharedConstructOutputs.indexTable.tableName,
          CHATBOT_TABLE_NAME: props.sharedConstructOutputs.chatbotTable.tableName,
          MODEL_TABLE_NAME: props.sharedConstructOutputs.modelTable.tableName,
          S3_BUCKET: s3Bucket.bucketName,
          EMBEDDING_MODEL_ENDPOINT: props.modelConstructOutputs.defaultEmbeddingModelName,
          AOS_ENDPOINT: domainEndpoint,
          KNOWLEDGE_BASE_ENABLED: props.config.knowledgeBase.enabled.toString(),
          KNOWLEDGE_BASE_TYPE: JSON.stringify(props.config.knowledgeBase.knowledgeBaseType || {}),
        },
        layers: [apiLambdaOnlineSourceLayer],
        statements: [this.iamHelper.dynamodbStatement,
                     this.iamHelper.logStatement,
                     this.iamHelper.secretStatement,
                     this.iamHelper.esStatement,
                     this.iamHelper.s3Statement,
                     this.iamHelper.bedrockStatement,
                     this.iamHelper.endpointStatement,
                    ],
      });

      const chatbotManagementLambda = new LambdaFunction(this, "ChatbotManagementLambda", {
        runtime: Runtime.PYTHON_3_12,
        code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
        handler: "chatbot_management.lambda_handler",
        environment: {
          INDEX_TABLE_NAME: props.sharedConstructOutputs.indexTable.tableName,
          CHATBOT_TABLE_NAME: props.sharedConstructOutputs.chatbotTable.tableName,
          MODEL_TABLE_NAME: props.sharedConstructOutputs.modelTable.tableName,
          EMBEDDING_ENDPOINT: props.modelConstructOutputs.defaultEmbeddingModelName,
        },
        layers: [apiLambdaOnlineSourceLayer],
        statements: [this.iamHelper.dynamodbStatement,
                      this.iamHelper.logStatement],
      });

      // Define the API Gateway Lambda Integration with proxy and no integration responses
      const lambdaChatHistoryIntegration = new apigw.LambdaIntegration(chatHistoryLambda.function, {
        proxy: true,
      });

      const apiResourceDdb = api.root.addResource("chat-history");
      apiResourceDdb.addMethod("POST", lambdaChatHistoryIntegration, this.genMethodOption(api, auth, null),);
      const apiResourceListSessions = apiResourceDdb.addResource("sessions");
      apiResourceListSessions.addMethod("GET", new apigw.LambdaIntegration(listSessionsLambda.function), this.genMethodOption(api, auth, null),);
      const apiResourceListMessages = apiResourceDdb.addResource("messages");
      apiResourceListMessages.addMethod("GET", new apigw.LambdaIntegration(listMessagesLambda.function), this.genMethodOption(api, auth, null),);

      const lambdaChatbotIntegration = new apigw.LambdaIntegration(chatbotManagementLambda.function, {
        proxy: true,
      });
      const apiResourceChatbotManagement = api.root.addResource("chatbot-management");
      // const chatbotResource = apiResourceChatbotManagement.addResource('chatbot');
      const apiResourceCheckChatbot = apiResourceChatbotManagement.addResource('check-chatbot');
      apiResourceCheckChatbot.addMethod("POST", lambdaChatbotIntegration, this.genMethodOption(api, auth, null));
      const apiResourceChatbots = apiResourceChatbotManagement.addResource("chatbots");
      apiResourceChatbots.addMethod("POST", lambdaChatbotIntegration, {
        ...this.genMethodOption(api, auth, {
          chatbotId: {type: JsonSchemaType.STRING},
          groupName: {type: JsonSchemaType.STRING},
          indexIds: {
             type: JsonSchemaType.OBJECT,
             properties: {
              qq: { type: JsonSchemaType.STRING },
              qd: { type: JsonSchemaType.STRING },
              intention: { type: JsonSchemaType.STRING }
             }
          },
          Message: {type: JsonSchemaType.STRING},
        }),
        requestModels: this.genRequestModel(api, {
          "chatbotId": { "type": JsonSchemaType.STRING },
          "index": {type: JsonSchemaType.OBJECT,
                    properties: {
                      qq: { type: JsonSchemaType.STRING },
                      qd: { type: JsonSchemaType.STRING },
                      intention: { type: JsonSchemaType.STRING }
                    },
                    required: ['qq','qd','intention']},
                    modelId: { "type": JsonSchemaType.STRING },
                    modelName: { "type": JsonSchemaType.STRING }
                   })
            });
      apiResourceChatbots.addMethod("GET", lambdaChatbotIntegration, {...this.genMethodOption(api, auth, {
        Items: {type: JsonSchemaType.ARRAY, items: {
          type: JsonSchemaType.OBJECT,
          properties: {
            ChatbotId: { type: JsonSchemaType.STRING },
            ModelName: { type: JsonSchemaType.STRING },
            ModelId: { type: JsonSchemaType.STRING },
            LastModifiedTime: { type: JsonSchemaType.STRING }
          },
          required: ['ChatbotId',
                    'ModelName',
                    'ModelId',
                    'LastModifiedTime'],
        }
        },
        Count: { type: JsonSchemaType.INTEGER },
        Config: { type: JsonSchemaType.OBJECT,
                  properties: {
                    MaxItems: { type: JsonSchemaType.INTEGER },
                    PageSize: { type: JsonSchemaType.INTEGER },
                    StartingToken: { type: JsonSchemaType.NULL }
                  }
        },
        chatbot_ids: {
          type: JsonSchemaType.ARRAY, items: {
            type: JsonSchemaType.STRING,
          }
        }
      })
      ,
        requestParameters: {
          'method.request.querystring.max_items': false,
          'method.request.querystring.page_size': false
        }
      })

      // const apiGetChatbotById = chatbotResource.addResource("{chatbotId}");
      // apiGetChatbotById.addMethod(
      //   "GET",
      //   new apigw.LambdaIntegration(chatbotManagementLambda.function),
      //   {
      //     ...this.genMethodOption(api, auth, {
      //       Items: {
      //         type: JsonSchemaType.ARRAY, items: {
      //           type: JsonSchemaType.OBJECT,
      //           properties: {
      //             chatbotId: { type: JsonSchemaType.STRING },
      //             index: { type: JsonSchemaType.STRING },
      //             model: { type: JsonSchemaType.STRING },
      //           },
      //           required: ['chatbotId', 'index', 'model'],
      //         }
      //       },
      //       Count: { type: JsonSchemaType.INTEGER }
      //     }),
      //     requestParameters: {
      //       'method.request.path.chatbotId': true
      //     },
      //     // requestModels: this.genRequestModel(api, {
      //     //   "executionId": { "type": JsonSchemaType.ARRAY, "items": {"type": JsonSchemaType.STRING}},
      //     // })
      //   }
      // );




      // const apiResourceChatbot = apiResourceChatbotManagement.addResource("chatbot");
      // const apiResourceChatbotDetail = apiResourceChatbot.addResource('{chatbotId}')
      // apiResourceChatbotDetail.addMethod("GET", lambdaChatbotIntegration, this.genMethodOption(api, auth, null));

      const apiResourceChatbotManagementEmbeddings = apiResourceChatbotManagement.addResource("embeddings")
      apiResourceChatbotManagementEmbeddings.addMethod("GET", lambdaChatbotIntegration, this.genMethodOption(api, auth, null));

      const apiResourceChatbotProxy = apiResourceChatbots.addResource("{proxy+}")
      apiResourceChatbotProxy.addMethod("DELETE", lambdaChatbotIntegration, this.genMethodOption(api, auth, null),);
      apiResourceChatbotProxy.addMethod("GET", lambdaChatbotIntegration, this.genMethodOption(api, auth, null),);

      // Define the API Gateway Lambda Integration to manage prompt
      const lambdaPromptIntegration = new apigw.LambdaIntegration(promptManagementLambda.function, {
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
      apiResourcePromptProxy.addMethod("POST", lambdaPromptIntegration, this.genMethodOption(api, auth, null));
      apiResourcePromptProxy.addMethod("DELETE", lambdaPromptIntegration, this.genMethodOption(api, auth, null));
      apiResourcePromptProxy.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(api, auth, null));

      // Define the API Gateway Lambda Integration to manage intention
      const lambdaIntentionIntegration = new apigw.LambdaIntegration(intentionLambda.function, {
        proxy: true,
      });
      const apiResourceIntentionManagement = api.root.addResource("intention");
      // apiResourceIntentionManagement.addMethod("DELETE", lambdaIntentionIntegration, this.genMethodOption(api, auth, null))
      const indexScan = apiResourceIntentionManagement.addResource("index-used-scan")
      indexScan.addMethod("POST", lambdaIntentionIntegration, this.genMethodOption(api, auth, null));
      // apiResourceIntentionManagement.addMethod("DELETE", lambdaIntentionIntegration, this.genMethodOption(api, auth, null));
      const presignedUrl = apiResourceIntentionManagement.addResource("execution-presigned-url");
      presignedUrl.addMethod("POST", lambdaIntentionIntegration, {
        ...this.genMethodOption(api, auth, {
          data: { type: JsonSchemaType.STRING },
          message: { type: JsonSchemaType.STRING },
          s3Bucket: { type: JsonSchemaType.STRING },
          s3Prefix: { type: JsonSchemaType.STRING }
        }),
        requestModels: this.genRequestModel(api, {
          "content_type": { "type": JsonSchemaType.STRING },
          "file_name": { "type": JsonSchemaType.STRING },
        })
      })
      const apiResourceDownload = apiResourceIntentionManagement.addResource("download-template");
      apiResourceDownload.addMethod("GET", lambdaIntentionIntegration, this.genMethodOption(api, auth, null));
      const apiResourceExecutionManagement = apiResourceIntentionManagement.addResource("executions");
      apiResourceExecutionManagement.addMethod("DELETE", lambdaIntentionIntegration, this.genMethodOption(api, auth, null))
      apiResourceExecutionManagement.addMethod("POST", lambdaIntentionIntegration, {
        ...this.genMethodOption(api, auth, {
          execution_id: { type: JsonSchemaType.STRING },
          input_payload: {
            type: JsonSchemaType.OBJECT,
            properties: {
              tableItemId: { type: JsonSchemaType.STRING },
              chatbotId: { type: JsonSchemaType.STRING },
              groupName: { type: JsonSchemaType.STRING },
              index: { type: JsonSchemaType.STRING },
              model: { type: JsonSchemaType.STRING },
              fieldName: { type: JsonSchemaType.STRING }
            }
          },
          result: { type: JsonSchemaType.STRING }
        }),
        requestModels: this.genRequestModel(api, {
          "chatbotId": { "type": JsonSchemaType.STRING },
          "index": { "type": JsonSchemaType.STRING },
          "model": { "type": JsonSchemaType.STRING },
          "s3Bucket": { "type": JsonSchemaType.STRING },
          "s3Prefix": { "type": JsonSchemaType.STRING }
        })
      });
      apiResourceExecutionManagement.addMethod("GET", lambdaIntentionIntegration, {...this.genMethodOption(api, auth, {
        Items: {type: JsonSchemaType.ARRAY, items: {
          type: JsonSchemaType.OBJECT,
          properties: {
            model: { type: JsonSchemaType.STRING },
            executionStatus: { type: JsonSchemaType.STRING },
            index: { type: JsonSchemaType.STRING },
            fileName: { type: JsonSchemaType.STRING },     
            createTime: { type: JsonSchemaType.STRING },
            createBy: { type: JsonSchemaType.STRING },
            executionId: { type: JsonSchemaType.STRING },

            chatbotId: { type: JsonSchemaType.STRING },
            details: { type: JsonSchemaType.STRING },
            tag: { type: JsonSchemaType.STRING },
          },
          required: ['model',
                    'executionStatus',
                    'index',
                    'fileName',
                    'createTime',
                    'createBy',
                    'executionId',
                    'chatbotId',
                    'details',
                    'tag'],
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
        }
      });
      const apiGetIntentionById = apiResourceExecutionManagement.addResource("{executionId}");
      apiGetIntentionById.addMethod(
        "GET",
        lambdaIntentionIntegration,
        {
          ...this.genMethodOption(api, auth, {
            Items: {
              type: JsonSchemaType.ARRAY, 
              items: {
                type: JsonSchemaType.OBJECT,
                properties: {
                  s3Path: { type: JsonSchemaType.STRING },
                  s3Prefix: { type: JsonSchemaType.STRING },
                  createTime: { type: JsonSchemaType.STRING }, // Consider using format: 'date-time'                
                  status: { type: JsonSchemaType.STRING },
                  QAList: {
                    type: JsonSchemaType.ARRAY,
                    items: {
                      type: JsonSchemaType.OBJECT,
                      properties: {
                        question: { type: JsonSchemaType.STRING },
                        intention: { type: JsonSchemaType.STRING },
                        kwargs: { type: JsonSchemaType.STRING },
                      }
                    }
                  }
                },
                required: ['s3Path', 's3Prefix', 'createTime', 'status','executionId'],
              }
            },
            Count: { type: JsonSchemaType.INTEGER }
          }),
          requestParameters: {
            'method.request.path.intentionId': true
          },
        }
      );
      // const apiUploadIntention = apiResourceIntentionManagement.addResource("upload");
      // apiUploadIntention.addMethod("POST", lambdaIntentionIntegration, this.genMethodOption(api, auth, null))
      
      
      // Define the API Gateway Lambda Integration with proxy and no integration responses
      const lambdaExecutorIntegration = new apigw.LambdaIntegration(
        props.chatStackOutputs.lambdaOnlineMain,
        { proxy: true },
      );

      // Define the API Gateway Method
      const apiResourceLLM = api.root.addResource("llm");
      apiResourceLLM.addMethod("POST", lambdaExecutorIntegration, this.genMethodOption(api, auth, null));

      const lambdaDispatcher = new LambdaFunction(this, "lambdaDispatcher", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/dispatcher")),
        environment: {
          SQS_QUEUE_URL: messageQueue.queueUrl,
        },
        statements: [sqsStatement],
      });

      const webSocketApi = new WebSocketConstruct(this, "WebSocketApi", {
        dispatcherLambda: lambdaDispatcher.function,
        sendMessageLambda: props.chatStackOutputs.lambdaOnlineMain,
        customAuthorizerLambda: customAuthorizerLambda.function,
      });
      let wsStage = webSocketApi.websocketApiStage
      this.wsEndpoint = `${wsStage.api.apiEndpoint}/${wsStage.stageName}/`;

    }

    // const plan = api.addUsagePlan('ExternalUsagePlan', {
    //   name: 'external-api-usage-plan'
    // });
    
    // This is not safe, but for the purpose of the test, we will use this
    // For deployment, we suggest user manually create the key and use it on the console

    // const apiKeyValue = this.makeApiKey(24);
    // const key = api.addApiKey('ApiKey', {
    //   value: apiKeyValue,
    // });
    
    // plan.addApiKey(key);
    // plan.addApiStage({
    //   stage: api.deploymentStage
    // })

    this.apiEndpoint = api.url;
    this.documentBucket = s3Bucket.bucketName;
    // this.apiKey = apiKeyValue;
  }

  private makeApiKey(length: number) {
    let apiKeyValue = '';
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    const charactersLength = characters.length;
    let counter = 0;
    while (counter < length) {
      apiKeyValue += characters.charAt(Math.floor(Math.random() * charactersLength));
      counter += 1;
    }
    return apiKeyValue;
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
      // apiKeyRequired: true,
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