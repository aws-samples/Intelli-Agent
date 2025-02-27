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

import { StackProps, NestedStack } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import { Construct } from "constructs";
import { join } from "path";

import { Constants } from "../shared/constants";
import { LambdaLayers } from "../shared/lambda-layers";
import { QueueConstruct } from "./chat-queue";
import { IAMHelper } from "../shared/iam-helper";
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Queue } from 'aws-cdk-lib/aws-sqs';
import { SystemConfig } from "../shared/types";
import { SharedConstructOutputs } from "../shared/shared-construct";
import { ModelConstructOutputs } from "../model/model-construct";
import { ChatTablesConstruct } from "./chat-tables";
import { LambdaFunction } from "../shared/lambda-helper";
import { Runtime, Code, Function } from "aws-cdk-lib/aws-lambda";
import { ConnectConstruct } from "../connect/connect-construct";


interface ChatStackProps extends StackProps {
  readonly config: SystemConfig;
  readonly sharedConstructOutputs: SharedConstructOutputs;
  readonly modelConstructOutputs: ModelConstructOutputs;
  readonly domainEndpoint?: string;
}

export interface ChatStackOutputs {
  sessionsTableName: string;
  messagesTableName: string;
  promptTableName: string;
  intentionTableName: string;
  sqsStatement: iam.PolicyStatement;
  messageQueue: Queue;
  dlq: Queue;
  lambdaOnlineMain: Function;
}

export class ChatStack extends NestedStack implements ChatStackOutputs {

  public sessionsTableName: string;
  public messagesTableName: string;
  public promptTableName: string;
  public intentionTableName: string;
  public stopSignalsTableName: string;
  public sqsStatement: iam.PolicyStatement;
  public messageQueue: Queue;
  public dlq: Queue;
  public lambdaOnlineMain: Function;

  private iamHelper: IAMHelper;
  private indexTableName: string;
  private modelTableName: string;
  private lambdaOnlineQueryPreprocess: Function;
  private lambdaOnlineIntentionDetection: Function;
  private lambdaOnlineAgent: Function;
  private lambdaOnlineLLMGenerate: Function;

  constructor(scope: Construct, id: string, props: ChatStackProps) {
    super(scope, id);

    this.iamHelper = props.sharedConstructOutputs.iamHelper;
    const vpc = props.sharedConstructOutputs.vpc;
    const securityGroups = props.sharedConstructOutputs.securityGroups;
    const domainEndpoint = props.domainEndpoint ?? '';

    const chatTablesConstruct = new ChatTablesConstruct(this, "chat-tables");

    this.sessionsTableName = chatTablesConstruct.sessionsTableName;
    this.messagesTableName = chatTablesConstruct.messagesTableName;
    this.promptTableName = chatTablesConstruct.promptTableName;
    this.intentionTableName = chatTablesConstruct.intentionTableName;
    this.stopSignalsTableName = chatTablesConstruct.stopSignalsTableName;
    this.indexTableName = props.sharedConstructOutputs.indexTable.tableName;
    this.modelTableName = props.sharedConstructOutputs.modelTable.tableName;

    const chatQueueConstruct = new QueueConstruct(this, "LLMQueueStack", {
      namePrefix: Constants.API_QUEUE_NAME,
    });
    this.sqsStatement = chatQueueConstruct.sqsStatement;
    this.messageQueue = chatQueueConstruct.messageQueue;
    this.dlq = chatQueueConstruct.dlq;

    const lambdaLayers = new LambdaLayers(this);
    const apiLambdaOnlineSourceLayer = lambdaLayers.createOnlineMainLayer();
    // const modelLayer = lambdaLayers.createModelDeploymentLayer();


    const openAiKey = new secretsmanager.Secret(this, "OpenAiSecret", {
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ key: "ReplaceItWithRealKey" }),
        generateStringKey: "key",
      }
    });
    const lambdaOnlineMain = new LambdaFunction(this, "lambdaOnlineMain", {
      runtime: Runtime.PYTHON_3_12,
      handler: "lambda_main.main.lambda_handler",
      code: Code.fromCustomCommand(
        "/tmp/online_lambda_function_codes",
        ['bash', '-c', [
          "mkdir -p /tmp/online_lambda_function_codes",
          `cp -r ${join(__dirname, "../../../lambda/online/*")} /tmp/online_lambda_function_codes`,
          `cp ${join(__dirname, "../../../lambda/job/dep/llm_bot_dep/sm_utils.py")} /tmp/online_lambda_function_codes/`,
        ].join(' && ')
        ]
      ),
      memorySize: 4096,
      vpc: vpc,
      securityGroups: securityGroups,
      environment: {
        AOS_ENDPOINT: domainEndpoint,
        RERANK_ENDPOINT: props.modelConstructOutputs.defaultEmbeddingModelName,
        EMBEDDING_ENDPOINT: props.modelConstructOutputs.defaultEmbeddingModelName,
        CHATBOT_TABLE_NAME: props.sharedConstructOutputs.chatbotTable.tableName,
        SESSIONS_TABLE_NAME: chatTablesConstruct.sessionsTableName,
        MESSAGES_TABLE_NAME: chatTablesConstruct.messagesTableName,
        PROMPT_TABLE_NAME: chatTablesConstruct.promptTableName,
        INTENTION_TABLE_NAME: chatTablesConstruct.intentionTableName,
        STOP_SIGNALS_TABLE_NAME: chatTablesConstruct.stopSignalsTableName,
        MODEL_TABLE_NAME: this.modelTableName,
        INDEX_TABLE_NAME: this.indexTableName,
        OPENAI_KEY_ARN: openAiKey.secretArn,
        CONNECT_USER_ARN: "",
        CONNECT_DOMAIN_ID: "",
        CONNECT_BOT_ID: "admin",
        KNOWLEDGE_BASE_ENABLED: props.config.knowledgeBase.enabled.toString(),
        KNOWLEDGE_BASE_TYPE: JSON.stringify(props.config.knowledgeBase.knowledgeBaseType || {}),
        BEDROCK_REGION: props.config.chat.bedrockRegion,
        BEDROCK_AWS_ACCESS_KEY_ID: props.config.chat.bedrockAk || "",
        BEDROCK_AWS_SECRET_ACCESS_KEY: props.config.chat.bedrockSk || ""
      },
      // layers: [apiLambdaOnlineSourceLayer, modelLayer],
      layers: [apiLambdaOnlineSourceLayer]
    });
    this.lambdaOnlineMain = lambdaOnlineMain.function;

    this.lambdaOnlineMain.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "es:DescribeDomain",
          "secretsmanager:GetSecretValue",
          "bedrock:*",
          "lambda:InvokeFunction",
          "secretmanager:GetSecretValue",
          "cases:*",
          "connect:*",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );

    this.lambdaOnlineMain.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "cloudformation:Describe*",
          "cloudformation:EstimateTemplateCost",
          "cloudformation:Get*",
          "cloudformation:List*",
          "cloudformation:ValidateTemplate",
          "cloudformation:Detect*"
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );

    this.lambdaOnlineMain.addToRolePolicy(this.sqsStatement);
    this.lambdaOnlineMain.addEventSource(
      new lambdaEventSources.SqsEventSource(this.messageQueue, { batchSize: 1 }),
    );
    this.lambdaOnlineMain.addToRolePolicy(this.iamHelper.s3Statement);
    this.lambdaOnlineMain.addToRolePolicy(this.iamHelper.endpointStatement);
    this.lambdaOnlineMain.addToRolePolicy(this.iamHelper.dynamodbStatement);
    openAiKey.grantRead(this.lambdaOnlineMain);

    const lambdaOnlineQueryPreprocess = new LambdaFunction(this, "lambdaOnlineQueryPreprocess", {
      runtime: Runtime.PYTHON_3_12,
      handler: "query_preprocess.lambda_handler",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_query_preprocess"),
      ),
      memorySize: 4096,
      vpc: vpc,
      securityGroups: securityGroups,
      layers: [apiLambdaOnlineSourceLayer],
    });
    this.lambdaOnlineQueryPreprocess = lambdaOnlineQueryPreprocess.function;

    this.lambdaOnlineQueryPreprocess.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "es:DescribeDomain",
          "secretsmanager:GetSecretValue",
          "bedrock:*",
          "lambda:InvokeFunction",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    this.lambdaOnlineQueryPreprocess.addToRolePolicy(this.iamHelper.s3Statement);
    this.lambdaOnlineQueryPreprocess.addToRolePolicy(this.iamHelper.endpointStatement);
    this.lambdaOnlineQueryPreprocess.addToRolePolicy(this.iamHelper.dynamodbStatement);

    const lambdaOnlineIntentionDetection = new LambdaFunction(this, "lambdaOnlineIntentionDetection", {
      runtime: Runtime.PYTHON_3_12,
      handler: "intention_detection.lambda_handler",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_intention_detection"),
      ),
      memorySize: 4096,
      vpc: vpc,
      securityGroups: securityGroups,
      layers: [apiLambdaOnlineSourceLayer],
    });
    this.lambdaOnlineIntentionDetection = lambdaOnlineIntentionDetection.function;

    const lambdaOnlineAgent = new LambdaFunction(this, "lambdaOnlineAgent", {
      runtime: Runtime.PYTHON_3_12,
      handler: "agent.lambda_handler",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_agent"),
      ),
      memorySize: 4096,
      vpc: vpc,
      securityGroups: securityGroups,
      layers: [apiLambdaOnlineSourceLayer],
    });
    this.lambdaOnlineAgent = lambdaOnlineAgent.function;

    this.lambdaOnlineAgent.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "es:DescribeDomain",
          "secretsmanager:GetSecretValue",
          "bedrock:*",
          "lambda:InvokeFunction",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    this.lambdaOnlineAgent.addToRolePolicy(this.iamHelper.s3Statement);
    this.lambdaOnlineAgent.addToRolePolicy(this.iamHelper.endpointStatement);
    this.lambdaOnlineAgent.addToRolePolicy(this.iamHelper.dynamodbStatement);


    const lambdaOnlineLLMGenerate = new LambdaFunction(this, "lambdaOnlineLLMGenerate", {
      runtime: Runtime.PYTHON_3_12,
      handler: "llm_generate.lambda_handler",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_llm_generate"),
      ),
      memorySize: 4096,
      vpc: vpc,
      securityGroups: securityGroups,
      layers: [apiLambdaOnlineSourceLayer],
    });
    this.lambdaOnlineLLMGenerate = lambdaOnlineLLMGenerate.function;

    this.lambdaOnlineLLMGenerate.addToRolePolicy(
      new iam.PolicyStatement({
        // principals: [new iam.AnyPrincipal()],
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "es:DescribeDomain",
          "secretsmanager:GetSecretValue",
          "bedrock:*",
          "lambda:InvokeFunction",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    this.lambdaOnlineLLMGenerate.addToRolePolicy(this.iamHelper.s3Statement);
    this.lambdaOnlineLLMGenerate.addToRolePolicy(this.iamHelper.endpointStatement);
    this.lambdaOnlineLLMGenerate.addToRolePolicy(this.iamHelper.dynamodbStatement);

    this.lambdaOnlineQueryPreprocess.grantInvoke(this.lambdaOnlineMain);

    this.lambdaOnlineIntentionDetection.grantInvoke(this.lambdaOnlineMain);

    this.lambdaOnlineAgent.grantInvoke(this.lambdaOnlineMain);

    this.lambdaOnlineLLMGenerate.grantInvoke(this.lambdaOnlineMain);
    this.lambdaOnlineLLMGenerate.grantInvoke(this.lambdaOnlineQueryPreprocess);
    this.lambdaOnlineLLMGenerate.grantInvoke(this.lambdaOnlineAgent);

    // this.lambdaOnlineFunctions.grantInvoke(this.lambdaOnlineMain);
    // this.lambdaOnlineFunctions.grantInvoke(this.lambdaOnlineIntentionDetection);

    if (props.config.chat.amazonConnect.enabled) {
      new ConnectConstruct(this, "connect-construct", {
        lambdaOnlineMain: lambdaOnlineMain.function,
      });
    }
  }
}
