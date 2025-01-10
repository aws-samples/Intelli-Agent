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
import { Runtime, Code } from 'aws-cdk-lib/aws-lambda';
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
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import { BundlingFileAccess, PhysicalName } from 'aws-cdk-lib/core';
import { PromptApi } from "./prompt-management";
import { IntentionApi } from "./intention-management";
import { ModelApi } from "./model-management";
import { ChatHistoryApi } from "./chat-history";

interface ApiStackProps extends StackProps {
  config: SystemConfig;
  sharedConstructOutputs: SharedConstructOutputs;
  modelConstructOutputs: ModelConstructOutputs;
  knowledgeBaseStackOutputs: KnowledgeBaseStackOutputs;
  chatStackOutputs: ChatStackOutputs;
  userPoolId: string;
  oidcClientId: string;
  // userConstructOutputs: UserConstructOutputs;
}

export interface ApiConstructOutputs {
  api: apigw.RestApi;
  auth: apigw.RequestAuthorizer;
  genMethodOption: any;
  customAuthorizerLambda: LambdaFunction;
  wsEndpoint: string;
}

export class ApiConstruct extends Construct implements ApiConstructOutputs {
  public apiEndpoint: string = "";
  public documentBucket: string = "";
  public wsEndpoint: string = "";
  public wsEndpointV2: string = "";
  public api: apigw.RestApi;
  public auth: apigw.RequestAuthorizer;
  public customAuthorizerLambda: LambdaFunction;
  public genMethodOption = (api: apigw.RestApi, auth: apigw.RequestAuthorizer, properties: any) => {
    let responseModel = apigw.Model.EMPTY_MODEL
    if (properties !== null) {
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
    const sharedLayer = lambdaLayers.createSharedLayer();
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
            s3.HttpMethods.HEAD,
          ],
          allowedOrigins: ["*"],
          allowedHeaders: ["*"],
          exposedHeaders: [
            "Access-Control-Allow-Origin",
          ],
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
    this.api = new apigw.RestApi(this, `${Constants.SOLUTION_SHORT_NAME.toLowerCase()}-api`, {
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

    this.customAuthorizerLambda = new LambdaFunction(this, "CustomAuthorizerLambda", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/authorizer")),
      handler: "custom_authorizer.lambda_handler",
      environment: {
        USER_POOL_ID: props.userPoolId,
        REGION: Aws.REGION,
        APP_CLIENT_ID: props.oidcClientId,
        // DEPLOYMENT_TIMESTAMP: Date.now().toString(),
      },
      layers: [apiLambdaAuthorizerLayer],
      statements: [props.sharedConstructOutputs.iamHelper.logStatement],
    });


    this.auth = new apigw.RequestAuthorizer(this, 'ApiAuthorizer', {
      handler: this.customAuthorizerLambda.function,
      identitySources: [apigw.IdentitySource.header('Authorization')],
    });

    // if (props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled) {
    if (props.config.knowledgeBase.enabled && props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled) {
      const executionManagementLambda = new LambdaFunction(this, "ExecutionManagementLambda", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
        handler: "execution_management.lambda_handler",
        environment: {
          EXECUTION_TABLE: executionTableName,
          ETL_OBJECT_TABLE: etlObjTableName,
          ETL_OBJECT_INDEX: etlObjIndexName,
          SFN_ARN: props.knowledgeBaseStackOutputs.sfnOutput.stateMachineArn,
        },
        statements: [this.iamHelper.dynamodbStatement],
      });

      props.knowledgeBaseStackOutputs.sfnOutput.grantStartExecution(executionManagementLambda.function);

      const uploadDocLambda = new LambdaFunction(this, "UploadDocument", {
        code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
        handler: "upload_document.lambda_handler",
        environment: {
          S3_BUCKET: s3Bucket.bucketName,
        },
        statements: [this.iamHelper.s3Statement],
      });

      const apiResourceStepFunction = this.api.root.addResource("knowledge-base");
      const apiKBExecution = apiResourceStepFunction.addResource("executions");
      if (props.knowledgeBaseStackOutputs.sfnOutput !== undefined) {
        // Integration with Step Function to trigger ETL process
        // Lambda function to trigger Step Function
        const sfnLambda = new LambdaFunction(this, "StepFunctionLambda", {
          code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
          handler: "sfn_handler.handler",
          environment: {
            SFN_ARN: props.knowledgeBaseStackOutputs.sfnOutput.stateMachineArn,
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
            ...this.genMethodOption(this.api, this.auth, null),
            requestModels: this.genRequestModel(this.api, {
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
        new apigw.LambdaIntegration(executionManagementLambda.function),
        {
          ...this.genMethodOption(this.api, this.auth, {
            Items: {
              type: JsonSchemaType.ARRAY, items: {
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
            Config: {
              type: JsonSchemaType.OBJECT,
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
        new apigw.LambdaIntegration(executionManagementLambda.function),
        {
          ...this.genMethodOption(this.api, this.auth, {
            ExecutionIds: { type: JsonSchemaType.ARRAY, items: { type: JsonSchemaType.STRING } },
            Message: { type: JsonSchemaType.STRING }
          }),
          requestModels: this.genRequestModel(this.api, {
            "executionId": { "type": JsonSchemaType.ARRAY, "items": { "type": JsonSchemaType.STRING } },
          })
        }
      );

      const apiGetExecutionById = apiKBExecution.addResource("{executionId}");
      apiGetExecutionById.addMethod(
        "GET",
        new apigw.LambdaIntegration(executionManagementLambda.function),
        {
          ...this.genMethodOption(this.api, this.auth, {
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
                required: ['s3Prefix', 's3Bucket', 'createTime', 's3Path', 'status', 'executionId'],
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
      apiGetExecutionById.addMethod("PUT", new apigw.LambdaIntegration(executionManagementLambda.function), this.genMethodOption(this.api, this.auth, null));


      const apiUploadDoc = apiResourceStepFunction.addResource("kb-presigned-url");
      apiUploadDoc.addMethod(
        "POST",
        new apigw.LambdaIntegration(uploadDocLambda.function),
        {
          ...
          this.genMethodOption(this.api, this.auth, {
            data: {
              type: JsonSchemaType.OBJECT,
              properties: {
                s3Bucket: { type: JsonSchemaType.STRING },
                s3Prefix: { type: JsonSchemaType.STRING },
                url: { type: JsonSchemaType.STRING }
              }
            },
            message: { type: JsonSchemaType.STRING }
          }),
          requestModels: this.genRequestModel(this.api, {
            "content_type": { "type": JsonSchemaType.STRING },
            "file_name": { "type": JsonSchemaType.STRING },
          })
        }
      );
    }

    if (props.config.chat.enabled) {
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
        layers: [sharedLayer],
        statements: [this.iamHelper.dynamodbStatement,
        this.iamHelper.logStatement],
      });

      const lambdaChatbotIntegration = new apigw.LambdaIntegration(chatbotManagementLambda.function, {
        proxy: true,
      });
      const apiResourceChatbotManagement = this.api.root.addResource("chatbot-management");
      // const chatbotResource = apiResourceChatbotManagement.addResource('chatbot');
      const apiResourceCheckDefaultChatbot = apiResourceChatbotManagement.addResource('default-chatbot');
      apiResourceCheckDefaultChatbot.addMethod("GET", lambdaChatbotIntegration, this.genMethodOption(this.api, this.auth, null));
      const apiResourceCheckChatbot = apiResourceChatbotManagement.addResource('check-chatbot');
      apiResourceCheckChatbot.addMethod("POST", lambdaChatbotIntegration, {
        ...this.genMethodOption(this.api, this.auth, {
          item: {type: JsonSchemaType.STRING || JsonSchemaType.NULL},
          reason: {type: JsonSchemaType.STRING || JsonSchemaType.NULL},
          result: {type: JsonSchemaType.BOOLEAN}
        }),
        requestModels: this.genRequestModel(this.api, {
          "chatbotId": { "type": JsonSchemaType.STRING },
          "index": {type: JsonSchemaType.OBJECT,
                    properties: {
                      qq: { type: JsonSchemaType.STRING },
                      qd: { type: JsonSchemaType.STRING },
                      intention: { type: JsonSchemaType.STRING }
                    },
                    required: ['qq','qd','intention']
                  },
          model: { "type": JsonSchemaType.STRING },
          type: { "type": JsonSchemaType.STRING }
          }
        )
      });
      const apiResourceCheckIndex = apiResourceChatbotManagement.addResource('check-index');
      apiResourceCheckIndex.addMethod("POST", lambdaChatbotIntegration, {
        ...this.genMethodOption(this.api, this.auth, {
          reason: {type: JsonSchemaType.STRING || JsonSchemaType.NULL},
          result: {type: JsonSchemaType.BOOLEAN}
        }),
        requestModels: this.genRequestModel(this.api, {
          "index": { "type": JsonSchemaType.STRING },
          "model": { "type": JsonSchemaType.STRING },
        })
      });
      const apiResourceListIndex = apiResourceChatbotManagement.addResource('indexes').addResource('{chatbotId}');
      apiResourceListIndex.addMethod("GET", lambdaChatbotIntegration, this.genMethodOption(this.api, this.auth, null));
      const apiResourceEditChatBot = apiResourceChatbotManagement.addResource('edit-chatbot');
      apiResourceEditChatBot.addMethod("POST", lambdaChatbotIntegration, this.genMethodOption(this.api, this.auth, null));
      const apiResourceChatbots = apiResourceChatbotManagement.addResource("chatbots");
      apiResourceChatbots.addMethod("POST", lambdaChatbotIntegration, {
        ...this.genMethodOption(this.api, this.auth, {
          chatbotId: { type: JsonSchemaType.STRING },
          groupName: { type: JsonSchemaType.STRING },
          indexIds: {
             type: JsonSchemaType.ARRAY,
             items: {type: JsonSchemaType.STRING}
          },
          modelType: {type: JsonSchemaType.STRING},
          Message: {type: JsonSchemaType.STRING},
        }),
        requestModels: this.genRequestModel(this.api, {
          "chatbotId": { "type": JsonSchemaType.STRING },
          "index": {type: JsonSchemaType.OBJECT,
                    properties: {
                      qq: { type: JsonSchemaType.STRING },
                      qd: { type: JsonSchemaType.STRING },
                      intention: { type: JsonSchemaType.STRING }
                    },
                    required: ['qq','qd','intention']
                  },
          modelId: { "type": JsonSchemaType.STRING },
          modelName: { "type": JsonSchemaType.STRING },
          operatorType: { "type": JsonSchemaType.STRING }
          }
        )
      });
      apiResourceChatbots.addMethod("GET", lambdaChatbotIntegration, {
        ...this.genMethodOption(this.api, this.auth, {
          Items: {
            type: JsonSchemaType.ARRAY, items: {
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
          Config: {
            type: JsonSchemaType.OBJECT,
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

      const apiResourceChatbotManagementEmbeddings = apiResourceChatbotManagement.addResource("embeddings")
      apiResourceChatbotManagementEmbeddings.addMethod("GET", lambdaChatbotIntegration, this.genMethodOption(this.api, this.auth, null));

      const apiResourceChatbotProxy = apiResourceChatbots.addResource("{proxy+}")
      apiResourceChatbotProxy.addMethod("DELETE", lambdaChatbotIntegration, this.genMethodOption(this.api, this.auth, null),);
      apiResourceChatbotProxy.addMethod("GET", lambdaChatbotIntegration, this.genMethodOption(this.api, this.auth, null),);

      const chatHistoryApi = new ChatHistoryApi(
        scope, "ChatHistoryApi", {
          api: this.api,
          auth: this.auth,
          messagesTableName: messagesTableName,
          sessionsTableName: sessionsTableName,
          iamHelper: this.iamHelper,
          genMethodOption: this.genMethodOption,
        },
      );

      const promptApi = new PromptApi(
        scope, "PromptApi", {
          api: this.api,
          auth: this.auth,
          promptTableName: props.chatStackOutputs.promptTableName,
          sharedLayer: sharedLayer,
          iamHelper: this.iamHelper,
          genMethodOption: this.genMethodOption,
        },
      );
      promptApi.node.addDependency(chatHistoryApi);

      const intentionApi = new IntentionApi(
        scope, "IntentionApi", {
          api: this.api,
          auth: this.auth,
          vpc: vpc!,
          securityGroups: securityGroups!,
          intentionTableName: props.chatStackOutputs.intentionTableName,
          indexTable: props.sharedConstructOutputs.indexTable.tableName,
          chatbotTable: props.sharedConstructOutputs.chatbotTable.tableName,
          modelTable: props.sharedConstructOutputs.modelTable.tableName,
          s3Bucket: s3Bucket.bucketName,
          defaultEmbeddingModelName: props.modelConstructOutputs.defaultEmbeddingModelName,
          domainEndpoint: domainEndpoint,
          config: props.config,
          sharedLayer: sharedLayer,
          iamHelper: this.iamHelper,
          genMethodOption: this.genMethodOption,
          genRequestModel: this.genRequestModel,
        },
      );
      intentionApi.node.addDependency(promptApi);

      const modelApi = new ModelApi(
        scope, "ModelApi", {
          api: this.api,
          auth: this.auth,
          modelTable: props.sharedConstructOutputs.modelTable.tableName,
          sharedLayer: sharedLayer,
          iamHelper: this.iamHelper,
          genMethodOption: this.genMethodOption, 
        },
      );
      modelApi.node.addDependency(intentionApi);

      // Define the API Gateway Lambda Integration with proxy and no integration responses
      const lambdaExecutorIntegration = new apigw.LambdaIntegration(
        props.chatStackOutputs.lambdaOnlineMain,
        { proxy: true },
      );

      // Define the API Gateway Method
      const apiResourceLLM = this.api.root.addResource("llm");
      apiResourceLLM.addMethod("POST", lambdaExecutorIntegration, this.genMethodOption(this.api, this.auth, null));

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
        customAuthorizerLambda: this.customAuthorizerLambda.function,
      });
      let wsStage = webSocketApi.websocketApiStage
      this.wsEndpoint = `${wsStage.api.apiEndpoint}/${wsStage.stageName}/`;

    }

    this.apiEndpoint = this.api.url;
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

  genRequestModel = (api: apigw.RestApi, properties: any) => {
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