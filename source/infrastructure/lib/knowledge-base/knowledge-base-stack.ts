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

import { Aws, Duration, NestedStack, RemovalPolicy, StackProps, CustomResource } from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as iam from "aws-cdk-lib/aws-iam";
import { Architecture, Code, Function, Runtime } from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import { Construct } from "constructs";
import { join } from "path";
import { DynamoDBTable } from "../shared/table";
import * as glue from "@aws-cdk/aws-glue-alpha";
import { IAMHelper } from "../shared/iam-helper";

import { SystemConfig } from "../shared/types";
import { SharedConstructOutputs } from "../shared/shared-construct";
import { ModelConstructOutputs } from "../model/model-construct";
import { AOSConstruct } from "./os-stack";

interface KnowledgeBaseStackProps extends StackProps {
  readonly config: SystemConfig;
  readonly sharedConstructOutputs: SharedConstructOutputs
  readonly modelConstructOutputs: ModelConstructOutputs;
  readonly uiPortalBucketName?: string;
}

export interface KnowledgeBaseStackOutputs {
  readonly sfnOutput: sfn.StateMachine;
  readonly executionTableName: string;
  readonly etlObjTableName: string;
  readonly aosDomainEndpoint: string;
  readonly etlObjIndexName: string;
}

export class KnowledgeBaseStack extends NestedStack implements KnowledgeBaseStackOutputs {
  public etlObjIndexName: string = "ExecutionIdIndex";
  public executionTableName: string = "";
  public etlObjTableName: string = "";
  public aosDomainEndpoint: string = "";
  public sfnOutput: sfn.StateMachine;

  private iamHelper: IAMHelper;
  private uiPortalBucketName: string;
  private glueResultBucket: s3.Bucket;
  private dynamodbStatement: iam.PolicyStatement;
  private glueLibS3Bucket: s3.Bucket;


  constructor(scope: Construct, id: string, props: KnowledgeBaseStackProps) {
    super(scope, id, props);

    this.iamHelper = props.sharedConstructOutputs.iamHelper;
    this.uiPortalBucketName = props.uiPortalBucketName || "";
    this.glueResultBucket = props.sharedConstructOutputs.resultBucket;

    const aosConstruct = new AOSConstruct(this, "aos-construct", {
      osVpc: props.sharedConstructOutputs.vpc,
      securityGroup: props.sharedConstructOutputs.securityGroups,
      useCustomDomain: props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.vectorStore.opensearch.useCustomDomain,
      customDomainEndpoint: props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.vectorStore.opensearch.customDomainEndpoint,
    });
    this.aosDomainEndpoint = aosConstruct.domainEndpoint;
    this.glueLibS3Bucket = new s3.Bucket(this, "llm-bot-glue-lib-bucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });
    const createKnowledgeBaseTablesAndPoliciesResult = this.createKnowledgeBaseTablesAndPolicies(props);
    this.executionTableName = createKnowledgeBaseTablesAndPoliciesResult.executionTable.tableName;
    this.etlObjTableName = createKnowledgeBaseTablesAndPoliciesResult.etlObjTable.tableName;
    this.dynamodbStatement = createKnowledgeBaseTablesAndPoliciesResult.dynamodbStatement;

    this.sfnOutput = this.createKnowledgeBaseJob(props);

  }

  private createKnowledgeBaseTablesAndPolicies(props: any) {
    const idAttr = {
      name: "executionId",
      type: dynamodb.AttributeType.STRING,
    }
    const etlS3Path = {
      name: "s3Path",
      type: dynamodb.AttributeType.STRING,
    }
    const executionTable = new DynamoDBTable(this, "Execution", idAttr).table;
    executionTable.addGlobalSecondaryIndex({
      indexName: "BucketAndPrefixIndex",
      partitionKey: { name: "s3Bucket", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "s3Prefix", type: dynamodb.AttributeType.STRING },
    });
    const etlObjTable = new DynamoDBTable(this, "ETLObject", etlS3Path, idAttr).table;
    etlObjTable.addGlobalSecondaryIndex({
      indexName: this.etlObjIndexName,
      partitionKey: { name: "executionId", type: dynamodb.AttributeType.STRING },
    });

    const dynamodbStatement = this.iamHelper.createPolicyStatement(
      [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Describe*",
        "dynamodb:List*",
        "dynamodb:Scan",
      ],
      [
        executionTable.tableArn,
        etlObjTable.tableArn,
        props.sharedConstructOutputs.chatbotTable.tableArn,
      ],
    );

    return { executionTable, etlObjTable, dynamodbStatement };
  }


  private createKnowledgeBaseJob(props: any) {
    const connection = new glue.Connection(this, "GlueJobConnection", {
      type: glue.ConnectionType.NETWORK,
      subnet: props.sharedConstructOutputs.vpc.privateSubnets[0],
      securityGroups: props.sharedConstructOutputs.securityGroups,
    });

    const notificationLambda = new Function(this, "ETLNotification", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "notification.lambda_handler",
      runtime: Runtime.PYTHON_3_12,
      timeout: Duration.minutes(15),
      memorySize: 256,
      architecture: Architecture.X86_64,
      environment: {
        EXECUTION_TABLE: this.executionTableName ?? "",
        ETL_OBJECT_TABLE: this.etlObjTableName ?? "",
      },
    });
    notificationLambda.addToRolePolicy(this.iamHelper.logStatement);
    notificationLambda.addToRolePolicy(this.dynamodbStatement);

    // If this.region is cn-north-1 or cn-northwest-1, use the glue-job-script-cn.py
    const glueJobScript = "glue-job-script.py";


    const extraPythonFiles = new s3deploy.BucketDeployment(
      this,
      "extraPythonFiles",
      {
        sources: [
          s3deploy.Source.asset(
            join(__dirname, "../../../lambda/job/dep/dist"),
          ),
        ],
        destinationBucket: this.glueLibS3Bucket
      },
    );

    // Assemble the extra python files list using _S3Bucket.s3UrlForObject("llm_bot_dep-0.1.0-py3-none-any.whl") and _S3Bucket.s3UrlForObject("nougat_ocr-0.1.17-py3-none-any.whl") and convert to string
    const extraPythonFilesList = [
      this.glueLibS3Bucket.s3UrlForObject("llm_bot_dep-0.1.0-py3-none-any.whl"),
    ].join(",");



    const glueRole = new iam.Role(this, "ETLGlueJobRole", {
      assumedBy: new iam.ServicePrincipal("glue.amazonaws.com"),
      // The role is used by the glue job to access AOS and by default it has 1 hour session duration which is not enough for the glue job to finish the embedding injection
      maxSessionDuration: Duration.hours(12),
    });
    glueRole.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpHead",
          "bedrock:*",
          "glue:GetConnection",
          "glue:GetJobs",
          "glue:GetJob",
          "ec2:Describe*",
          "ec2:CreateNetworkInterface",
          "ec2:AttachNetworkInterface",
          "ec2:CreateTags",
          "secretsmanager:GetSecretValue",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    glueRole.addToPolicy(this.iamHelper.endpointStatement);
    glueRole.addToPolicy(this.iamHelper.s3Statement);
    glueRole.addToPolicy(this.iamHelper.logStatement);
    glueRole.addToPolicy(this.iamHelper.glueStatement);
    glueRole.addToPolicy(this.dynamodbStatement);
    glueRole.addToPolicy(this.iamHelper.dynamodbStatement);

    // Create glue job to process files specified in s3 bucket and prefix
    const glueJob = new glue.Job(this, "PythonShellJob", {
      executable: glue.JobExecutable.pythonShell({
        glueVersion: glue.GlueVersion.V3_0,
        pythonVersion: glue.PythonVersion.THREE_NINE,
        script: glue.Code.fromAsset(
          join(__dirname, "../../../lambda/job", glueJobScript),
        ),
      }),
      // Worker Type is not supported for Job Command pythonshell and Both workerType and workerCount must be set
      // workerType: glue.WorkerType.G_2X,
      // workerCount: 2,
      maxConcurrentRuns: 200,
      maxRetries: 1,
      connections: [connection],
      maxCapacity: 1,
      role: glueRole,
      defaultArguments: {
        "--AOS_ENDPOINT": this.aosDomainEndpoint,
        "--REGION": process.env.CDK_DEFAULT_REGION || "-",
        "--ETL_MODEL_ENDPOINT": props.modelConstructOutputs.defaultKnowledgeBaseModelName,
        "--RES_BUCKET": this.glueResultBucket.bucketName,
        "--ETL_OBJECT_TABLE": this.etlObjTableName || "-",
        "--PORTAL_BUCKET": this.uiPortalBucketName,
        "--CHATBOT_TABLE": props.sharedConstructOutputs.chatbotTable.tableName,
        "--additional-python-modules":
          "langchain==0.3.7,beautifulsoup4==4.12.2,requests-aws4auth==1.2.3,boto3==1.35.98,openai==0.28.1,pyOpenSSL==23.3.0,tenacity==8.2.3,markdownify==0.11.6,mammoth==1.6.0,chardet==5.2.0,python-docx==1.1.0,nltk==3.9.1,pdfminer.six==20221105,smart-open==7.0.4,opensearch-py==2.2.0,lxml==5.2.2,pandas==2.1.2,openpyxl==3.1.5,xlrd==2.0.1,langchain_community==0.3.5,pillow==10.0.1,tiktoken==0.8.0",
        // Add multiple extra python files
        "--extra-py-files": extraPythonFilesList
      },
    });

    // Create SNS topic and subscription to notify when glue job is completed
    const topic = new sns.Topic(this, "etl-topic", {
      displayName: "etl-topic",
    });
    topic.addSubscription(new subscriptions.EmailSubscription(props.config.email));
    topic.addSubscription(new subscriptions.LambdaSubscription(notificationLambda));

    // Lambda function to for file deduplication and glue job allocation based on file number
    const etlLambda = new Function(this, "ETLLambda", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "main.lambda_handler",
      runtime: Runtime.PYTHON_3_12,
      timeout: Duration.minutes(15),
      memorySize: 1024,
      architecture: Architecture.X86_64,
      environment: {
        DEFAULT_EMBEDDING_ENDPOINT:
          props.modelConstructOutputs.defaultEmbeddingModelName,
        AOS_DOMAIN_ENDPOINT: this.aosDomainEndpoint
      },
    });
    etlLambda.addToRolePolicy(this.iamHelper.glueStatement);
    etlLambda.addToRolePolicy(this.iamHelper.s3Statement);
    etlLambda.addToRolePolicy(this.iamHelper.logStatement);

    const lambdaETLIntegration = new tasks.LambdaInvoke(
      this,
      "lambdaETLIntegration",
      {
        lambdaFunction: etlLambda,
        // Use the result of this invocation to decide how many Glue jobs to run
        resultSelector: {
          processedPayload: {
            "s3Bucket.$": "$.Payload.s3Bucket",
            "s3Prefix.$": "$.Payload.s3Prefix",
            "qaEnhance.$": "$.Payload.qaEnhance",
            "chatbotId.$": "$.Payload.chatbotId",
            "groupName.$": "$.Payload.groupName",
            "indexId.$": "$.Payload.indexId",
            "embeddingModelType.$": "$.Payload.embeddingModelType",
            "offline.$": "$.Payload.offline",
            "batchFileNumber.$": "$.Payload.batchFileNumber",
            "batchIndices.$": "$.Payload.batchIndices",
            "indexType.$": "$.Payload.indexType",
            "operationType.$": "$.Payload.operationType",
            "embeddingEndpoint.$": "$.Payload.embeddingEndpoint",
            "tableItemId.$": "$.Payload.tableItemId",
            "documentLanguage.$": "$.Payload.documentLanguage",
          },
        },
        // Original input
        resultPath: "$.TaskResult",
        outputPath: "$.TaskResult.processedPayload",
      },
    );

    const offlineGlueJob = new tasks.GlueStartJobRun(this, "OfflineGlueJob", {
      glueJobName: glueJob.jobName,
      integrationPattern: sfn.IntegrationPattern.RUN_JOB,
      arguments: sfn.TaskInput.fromObject({
        "--AOS_ENDPOINT": this.aosDomainEndpoint,
        "--BATCH_FILE_NUMBER.$": "$.batchFileNumber",
        "--BATCH_INDICE.$": 'States.Format(\'{}\', $.batchIndices)',
        "--DOCUMENT_LANGUAGE.$": "$.documentLanguage",
        "--EMBEDDING_MODEL_ENDPOINT.$": "$.embeddingEndpoint",
        "--ETL_MODEL_ENDPOINT": props.modelConstructOutputs.defaultKnowledgeBaseModelName || "-",
        "--INDEX_TYPE.$": "$.indexType",
        "--JOB_NAME": glueJob.jobName,
        "--OFFLINE": "true",
        "--OPERATION_TYPE.$": "$.operationType",
        "--ETL_OBJECT_TABLE": this.etlObjTableName || "-",
        "--TABLE_ITEM_ID.$": "$.tableItemId",
        "--QA_ENHANCEMENT.$": "$.qaEnhance",
        "--REGION": process.env.CDK_DEFAULT_REGION || "-",
        "--BEDROCK_REGION": props.config.chat.bedrockRegion,
        "--MODEL_TABLE": props.sharedConstructOutputs.modelTable.tableName,
        "--RES_BUCKET": this.glueResultBucket.bucketName,
        "--S3_BUCKET.$": "$.s3Bucket",
        "--S3_PREFIX.$": "$.s3Prefix",
        "--PORTAL_BUCKET": this.uiPortalBucketName,
        "--CHATBOT_ID.$": "$.chatbotId",
        "--GROUP_NAME.$": "$.groupName",
        "--INDEX_ID.$": "$.indexId",
        "--EMBEDDING_MODEL_TYPE.$": "$.embeddingModelType",
        "--job-language": "python",
      }),
    });

    // Define a Map state to run multiple Glue jobs in parallel based on the number of files to process
    const mapState = new sfn.Map(this, "MapState", {
      // inputPath should point to the root since we want to pass the entire payload to the iterator
      inputPath: "$",
      // itemsPath should reference an array. We need to construct this array based on batchIndices
      itemsPath: sfn.JsonPath.stringAt("$.batchIndices"),
      // Set the max concurrency to 0 to run all the jobs in parallel
      maxConcurrency: 0,
      itemSelector: {
        // These parameters are passed to each iteration of the map state
        "s3Bucket.$": "$.s3Bucket",
        "s3Prefix.$": "$.s3Prefix",
        "chatbotId.$": "$.chatbotId",
        "groupName.$": "$.groupName",
        "indexId.$": "$.indexId",
        "embeddingModelType.$": "$.embeddingModelType",
        "qaEnhance.$": "$.qaEnhance",
        "offline.$": "$.offline",
        "batchFileNumber.$": "$.batchFileNumber",
        // "index" is a special variable within the Map state that represents the current index
        "batchIndices.$": "$$.Map.Item.Index", // Add this if you need to know the index of the current item in the map state
        "indexType.$": "$.indexType",
        "operationType.$": "$.operationType",
        "embeddingEndpoint.$": "$.embeddingEndpoint",
        "tableItemId.$": "$.tableItemId",
        "documentLanguage.$": "$.documentLanguage",
      },
      resultPath: "$.mapResults",
    });

    mapState.itemProcessor(
      offlineGlueJob.addRetry({
        errors: ["States.ALL"],
        interval: Duration.seconds(10),
        maxAttempts: 3,
      }),
    );

    // Notify the result of the glue job
    const notifyTask = new tasks.SnsPublish(this, "NotifyTask", {
      integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
      topic: topic,
      message: sfn.TaskInput.fromObject({
        "executionId.$": "$.tableItemId",
        "mapResults.$": "$.mapResults",
        "operationType.$": "$.operationType",
      }),
    });

    // Add the notify task to both online and offline branches
    mapState.next(notifyTask);

    const sfnDefinition = lambdaETLIntegration.next(mapState);

    const sfnStateMachine = new sfn.StateMachine(this, "ETLState", {
      definitionBody: sfn.DefinitionBody.fromChainable(sfnDefinition),
      stateMachineType: sfn.StateMachineType.STANDARD,
      // Glue job timeout
      timeout: Duration.minutes(2880),
    });

    return sfnStateMachine;
  }
}
