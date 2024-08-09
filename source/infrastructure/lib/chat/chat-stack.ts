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

import { Aws, Duration, StackProps, NestedStack } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import { Construct } from "constructs";
import { join } from "path";

import { Constants } from "../shared/constants";
import { LambdaLayers } from "../shared/lambda-layers";
import { QueueConstruct } from "./chat-queue";
import { Function, Runtime, Code, Architecture } from 'aws-cdk-lib/aws-lambda';
import { IAMHelper } from "../shared/iam-helper";
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Queue } from 'aws-cdk-lib/aws-sqs';
import { SystemConfig } from "../shared/types";
import { SharedConstructOutputs } from "../shared/shared-construct";
import { ModelConstructOutputs } from "../model/model-construct";
import { ChatTablesConstruct } from "./chat-tables";


interface ChatStackProps extends StackProps {
  readonly config: SystemConfig;
  readonly sharedConstructOutputs: SharedConstructOutputs;
  readonly modelConstructOutputs: ModelConstructOutputs;
  readonly domainEndpoint: string;
}

export interface ChatStackOutputs {
  sessionsTableName: string;
  messagesTableName: string;
  promptTableName: string;
  indexTableName: string;
  modelTableName: string;
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
  public indexTableName: string;
  public modelTableName: string;
  public intentionTableName: string;
  public sqsStatement: iam.PolicyStatement;
  public messageQueue: Queue;
  public dlq: Queue;
  public lambdaOnlineMain: Function;

  private iamHelper: IAMHelper;

  constructor(scope: Construct, id: string, props: ChatStackProps) {
    super(scope, id);

    this.iamHelper = props.sharedConstructOutputs.iamHelper;
    const vpc = props.sharedConstructOutputs.vpc;
    const securityGroup = props.sharedConstructOutputs.securityGroup;
    const domainEndpoint = props.domainEndpoint;

    const chatTablesConstruct = new ChatTablesConstruct(this, "chat-tables");

    this.sessionsTableName = chatTablesConstruct.sessionsTableName;
    this.messagesTableName = chatTablesConstruct.messagesTableName;
    this.promptTableName = chatTablesConstruct.promptTableName;
    this.indexTableName = chatTablesConstruct.indexTableName;
    this.modelTableName = chatTablesConstruct.modelTableName;
    this.intentionTableName = chatTablesConstruct.intentionTableName;

    const chatQueueConstruct = new QueueConstruct(this, "LLMQueueStack", {
      namePrefix: Constants.API_QUEUE_NAME,
    });
    this.sqsStatement = chatQueueConstruct.sqsStatement;
    this.messageQueue = chatQueueConstruct.messageQueue;
    this.dlq = chatQueueConstruct.dlq;

    const lambdaLayers = new LambdaLayers(this);
    const apiLambdaOnlineSourceLayer = lambdaLayers.createOnlineSourceLayer();
    const apiLambdaJobSourceLayer = lambdaLayers.createJobSourceLayer();


    const openAiKey = new secretsmanager.Secret(this, "OpenAiSecret", {
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ key: "ReplaceItWithRealKey" }),
        generateStringKey: "key",
      }
    });
    const lambdaOnlineMain = new Function(this, "lambdaOnlineMain", {
      runtime: Runtime.PYTHON_3_12,
      handler: "main.lambda_handler",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_main"),
      ),
      timeout: Duration.minutes(15),
      memorySize: 4096,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      layers: [apiLambdaOnlineSourceLayer, apiLambdaJobSourceLayer],
      environment: {
        AOS_ENDPOINT: domainEndpoint,
        RERANK_ENDPOINT: props.modelConstructOutputs.defaultEmbeddingModelName,
        EMBEDDING_ENDPOINT: props.modelConstructOutputs.defaultEmbeddingModelName,
        CHATBOT_TABLE_NAME: props.sharedConstructOutputs.chatbotTable.tableName,
        SESSIONS_TABLE_NAME: chatTablesConstruct.sessionsTableName,
        MESSAGES_TABLE_NAME: chatTablesConstruct.messagesTableName,
        PROMPT_TABLE_NAME: chatTablesConstruct.promptTableName,
        MODEL_TABLE_NAME: chatTablesConstruct.modelTableName,
        INDEX_TABLE_NAME: chatTablesConstruct.indexTableName,
        OPENAI_KEY_ARN: openAiKey.secretArn,
      },
    });

    lambdaOnlineMain.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "secretsmanager:GetSecretValue",
          "bedrock:*",
          "lambda:InvokeFunction",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    lambdaOnlineMain.addToRolePolicy(this.sqsStatement);
    lambdaOnlineMain.addEventSource(
      new lambdaEventSources.SqsEventSource(this.messageQueue, { batchSize: 1 }),
    );
    lambdaOnlineMain.addToRolePolicy(this.iamHelper.s3Statement);
    lambdaOnlineMain.addToRolePolicy(this.iamHelper.endpointStatement);
    lambdaOnlineMain.addToRolePolicy(this.iamHelper.dynamodbStatement);
    openAiKey.grantRead(lambdaOnlineMain);

    this.lambdaOnlineMain = lambdaOnlineMain;

    const lambdaOnlineQueryPreprocess = new Function(this, "lambdaOnlineQueryPreprocess", {
      runtime: Runtime.PYTHON_3_12,
      handler: "query_preprocess.lambda_handler",
      functionName: "Online_Query_Preprocess",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_query_preprocess"),
      ),
      timeout: Duration.minutes(15),
      memorySize: 4096,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      layers: [apiLambdaOnlineSourceLayer],
    });

    lambdaOnlineQueryPreprocess.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "secretsmanager:GetSecretValue",
          "bedrock:*",
          "lambda:InvokeFunction",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    lambdaOnlineQueryPreprocess.addToRolePolicy(this.iamHelper.s3Statement);
    lambdaOnlineQueryPreprocess.addToRolePolicy(this.iamHelper.endpointStatement);
    lambdaOnlineQueryPreprocess.addToRolePolicy(this.iamHelper.dynamodbStatement);

    const lambdaOnlineIntentionDetection = new Function(this, "lambdaOnlineIntentionDetection", {
      runtime: Runtime.PYTHON_3_12,
      handler: "intention_detection.lambda_handler",
      functionName: "Online_Intention_Detection",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_intention_detection"),
      ),
      timeout: Duration.minutes(15),
      memorySize: 4096,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      layers: [apiLambdaOnlineSourceLayer],
    });

    const lambdaOnlineAgent = new Function(this, "lambdaOnlineAgent", {
      runtime: Runtime.PYTHON_3_12,
      handler: "agent.lambda_handler",
      functionName: "Online_Agent",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_agent"),
      ),
      timeout: Duration.minutes(15),
      memorySize: 4096,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      layers: [apiLambdaOnlineSourceLayer],
    });

    lambdaOnlineAgent.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "secretsmanager:GetSecretValue",
          "bedrock:*",
          "lambda:InvokeFunction",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    lambdaOnlineAgent.addToRolePolicy(this.iamHelper.s3Statement);
    lambdaOnlineAgent.addToRolePolicy(this.iamHelper.endpointStatement);
    lambdaOnlineAgent.addToRolePolicy(this.iamHelper.dynamodbStatement);

    const lambdaOnlineLLMGenerate = new Function(this, "lambdaOnlineLLMGenerate", {
      runtime: Runtime.PYTHON_3_12,
      handler: "llm_generate.lambda_handler",
      functionName: "Online_LLM_Generate",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/lambda_llm_generate"),
      ),
      timeout: Duration.minutes(15),
      memorySize: 4096,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      layers: [apiLambdaOnlineSourceLayer],
    });

    lambdaOnlineLLMGenerate.addToRolePolicy(
      new iam.PolicyStatement({
        // principals: [new iam.AnyPrincipal()],
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "secretsmanager:GetSecretValue",
          "bedrock:*",
          "lambda:InvokeFunction",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    lambdaOnlineLLMGenerate.addToRolePolicy(this.iamHelper.s3Statement);
    lambdaOnlineLLMGenerate.addToRolePolicy(this.iamHelper.endpointStatement);
    lambdaOnlineLLMGenerate.addToRolePolicy(this.iamHelper.dynamodbStatement);

    const lambdaOnlineFunctions = new Function(this, "lambdaOnlineFunctions", {
      runtime: Runtime.PYTHON_3_12,
      handler: "lambda_tools.lambda_handler",
      functionName: "Online_Functions",
      code: Code.fromAsset(
        join(__dirname, "../../../lambda/online/functions/functions_utils"),
      ),
      timeout: Duration.minutes(15),
      memorySize: 4096,
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets,
      },
      securityGroups: [securityGroup],
      architecture: Architecture.X86_64,
      environment: {
        CHATBOT_TABLE: props.sharedConstructOutputs.chatbotTable.tableName,
        INDEX_TABLE: chatTablesConstruct.indexTableName,
        MODEL_TABLE: chatTablesConstruct.modelTableName,
      },
      layers: [apiLambdaOnlineSourceLayer, apiLambdaJobSourceLayer],
    });

    lambdaOnlineQueryPreprocess.grantInvoke(lambdaOnlineMain);

    lambdaOnlineIntentionDetection.grantInvoke(lambdaOnlineMain);

    lambdaOnlineAgent.grantInvoke(lambdaOnlineMain);

    lambdaOnlineLLMGenerate.grantInvoke(lambdaOnlineMain);
    lambdaOnlineLLMGenerate.grantInvoke(lambdaOnlineQueryPreprocess);
    lambdaOnlineLLMGenerate.grantInvoke(lambdaOnlineAgent);

    lambdaOnlineFunctions.grantInvoke(lambdaOnlineMain);
    lambdaOnlineFunctions.grantInvoke(lambdaOnlineIntentionDetection);


  }


}
