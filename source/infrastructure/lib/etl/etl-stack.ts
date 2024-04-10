import { Duration, NestedStack, RemovalPolicy, StackProps } from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import { Architecture, Code, Function, Runtime } from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import * as sagemaker from "aws-cdk-lib/aws-sagemaker";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import { Construct } from "constructs";
import { join } from "path";

import * as glue from "@aws-cdk/aws-glue-alpha";

import { BuildConfig } from "../shared/build-config";

interface ETLStackProps extends StackProps {
  etlVpc: ec2.Vpc;
  subnets: ec2.ISubnet[];
  securityGroups: ec2.SecurityGroup;
  domainEndpoint: string;
  embeddingEndpoint: string[];
  region: string;
  subEmail: string;
  s3ModelAssets: string;
  openSearchIndex: string;
  imageName: string;
  etlTag: string;
}

export class EtlStack extends NestedStack {
  public sfnOutput;
  public jobName;
  public jobArn;
  public processedObjectsTableName;
  public workspaceTableName;
  public etlEndpoint: string;
  public resBucketName: string;

  constructor(scope: Construct, id: string, props: ETLStackProps) {
    super(scope, id, props);

    const endpointRole = new iam.Role(this, "etl-endpoint-role", {
      assumedBy: new iam.ServicePrincipal("sagemaker.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonSageMakerFullAccess"),
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonS3FullAccess"),
        iam.ManagedPolicy.fromAwsManagedPolicyName("CloudWatchLogsFullAccess"),
      ],
    });

    const imageUrlDomain =
      this.region === "cn-north-1" || this.region === "cn-northwest-1"
        ? ".amazonaws.com.cn/"
        : ".amazonaws.com/";

    // If this.region is cn-notrh-1 or cn-northwest-1, use the glue-job-script-cn.py
    const glueJobScript =
      this.region === "cn-north-1" || this.region === "cn-northwest-1"
        ? "glue-job-script-cn.py"
        : "glue-job-script.py";

    // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
    const imageUrl =
      this.account +
      ".dkr.ecr." +
      this.region +
      imageUrlDomain +
      props.imageName +
      ":" +
      props.etlTag;
    const model = new sagemaker.CfnModel(this, "etl-model", {
      executionRoleArn: endpointRole.roleArn,
      primaryContainer: {
        image: imageUrl,
      },
    });

    // Create endpoint configuration
    const endpointConfig = new sagemaker.CfnEndpointConfig(
      this,
      "etl-endpoint-config",
      {
        productionVariants: [
          {
            initialVariantWeight: 1.0,
            modelName: model.attrModelName,
            variantName: "variantProd",
            containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
            initialInstanceCount: 1,
            instanceType: "ml.g4dn.2xlarge",
          },
        ],
      },
    );

    // Create endpoint
    const etlEndpoint = new sagemaker.CfnEndpoint(this, "etl-endpoint", {
      endpointConfigName: endpointConfig.attrEndpointConfigName,
      endpointName: "etl-endpoint",
    });

    if (typeof etlEndpoint.endpointName === "undefined") {
      throw new Error("etlEndpoint.endpointName is undefined");
    }

    this.etlEndpoint = etlEndpoint.endpointName;

    const connection = new glue.Connection(this, "GlueJobConnection", {
      type: glue.ConnectionType.NETWORK,
      subnet: props.subnets[0],
      securityGroups: [props.securityGroups],
    });

    const table = new dynamodb.Table(this, "ProcessedObjects", {
      partitionKey: { name: "ObjectKey", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    table.addGlobalSecondaryIndex({
      indexName: "BucketAndPrefixIndex",
      partitionKey: { name: "Bucket", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "Prefix", type: dynamodb.AttributeType.STRING },
    });

    // Add ExpiryTimestamp as an attribute but not as a sort key in the base table
    table.addGlobalSecondaryIndex({
      indexName: "ExpiryTimestampIndex",
      partitionKey: {
        name: "ExpiryTimestamp",
        type: dynamodb.AttributeType.NUMBER,
      },
    });

    const workspaceTable = new dynamodb.Table(this, "WorkspaceTable", {
      partitionKey: {
        name: "workspace_id",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "object_type",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    workspaceTable.addGlobalSecondaryIndex({
      indexName: "by_object_type_idx",
      partitionKey: {
        name: "object_type",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "created_at",
        type: dynamodb.AttributeType.STRING,
      },
    });

    const s3Bucket = new s3.Bucket(this, "llm-bot-glue-result-bucket", {
      // bucketName: `llm-bot-glue-lib-${Aws.ACCOUNT_ID}-${Aws.REGION}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    const glueLibS3Bucket = new s3.Bucket(this, "llm-bot-glue-lib-bucket", {
      // bucketName: `llm-bot-glue-lib-${Aws.ACCOUNT_ID}-${Aws.REGION}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    const extraPythonFiles = new s3deploy.BucketDeployment(
      this,
      "extraPythonFiles",
      {
        sources: [
          s3deploy.Source.asset(
            join(__dirname, "../../../lambda/job/dep/dist"),
          ),
        ],
        destinationBucket: glueLibS3Bucket,
        // destinationKeyPrefix: "llm_bot_dep-0.1.0-py3-none-any.whl",
      },
    );

    // Assemble the extra python files list using _S3Bucket.s3UrlForObject("llm_bot_dep-0.1.0-py3-none-any.whl") and _S3Bucket.s3UrlForObject("nougat_ocr-0.1.17-py3-none-any.whl") and convert to string
    const extraPythonFilesList = [
      glueLibS3Bucket.s3UrlForObject("llm_bot_dep-0.1.0-py3-none-any.whl"),
    ].join(",");

    const glueRole = new iam.Role(this, "ETLGlueJobRole", {
      assumedBy: new iam.ServicePrincipal("glue.amazonaws.com"),
      // The role is used by the glue job to access AOS and by default it has 1 hour session duration which is not enough for the glue job to finish the embedding injection
      maxSessionDuration: Duration.hours(12),
    });
    glueRole.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          "sagemaker:InvokeEndpointAsync",
          "sagemaker:InvokeEndpoint",
          "s3:*",
          "es:*",
          "glue:*",
          "ec2:*",
          "dynamodb:*",
          "bedrock:*",
          // CloudWatch logs
          "logs:*",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );

    // Creata glue job to process files speicified in s3 bucket and prefix
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
        "--AOS_ENDPOINT": props.domainEndpoint,
        "--REGION": props.region,
        "--ETL_MODEL_ENDPOINT": this.etlEndpoint,
        "--DOC_INDEX_TABLE": props.openSearchIndex,
        "--RES_BUCKET": s3Bucket.bucketName,
        "--ProcessedObjectsTable": table.tableName,
        "--WORKSPACE_TABLE": workspaceTable.tableName,
        "--additional-python-modules":
          "langchain==0.1.11,beautifulsoup4==4.12.2,requests-aws4auth==1.2.3,boto3==1.28.84,openai==0.28.1,pyOpenSSL==23.3.0,tenacity==8.2.3,markdownify==0.11.6,mammoth==1.6.0,chardet==5.2.0,python-docx==1.1.0,nltk==3.8.1,pdfminer.six==20221105",
        "--python-modules-installer-option": BuildConfig.JOB_PIP_OPTION,
        // add multiple extra python files
        "--extra-py-files": extraPythonFilesList,
      },
    });

    // Create SNS topic and subscription to notify when glue job is completed
    const topic = new sns.Topic(this, "etl-topic", {
      displayName: "etl-topic",
      topicName: "etl-topic",
    });
    topic.addSubscription(new subscriptions.EmailSubscription(props.subEmail));

    // Lambda function to for file deduplication and glue job allocation based on file number
    const lambdaETL = new Function(this, "lambdaETL", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "main.lambda_handler",
      runtime: Runtime.PYTHON_3_11,
      timeout: Duration.minutes(15),
      memorySize: 1024,
      architecture: Architecture.X86_64,
      environment: {
        DEFAULT_EMBEDDING_ENDPOINT:
          props.embeddingEndpoint[0] ||
          "Default Embedding Endpoint Not Created",
      },
    });

    lambdaETL.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          // Glue job
          "glue:StartJobRun",
          "s3:List*",
          "s3:Put*",
          "s3:Get*",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );

    const lambdaETLIntegration = new tasks.LambdaInvoke(
      this,
      "lambdaETLIntegration",
      {
        lambdaFunction: lambdaETL,
        // Use the result of this invocation to decide how many Glue jobs to run
        resultSelector: {
          processedPayload: {
            "s3Bucket.$": "$.Payload.s3Bucket",
            "s3Prefix.$": "$.Payload.s3Prefix",
            "qaEnhance.$": "$.Payload.qaEnhance",
            "workspaceId.$": "$.Payload.workspaceId",
            "offline.$": "$.Payload.offline",
            "batchFileNumber.$": "$.Payload.batchFileNumber",
            "batchIndices.$": "$.Payload.batchIndices",
            "indexType.$": "$.Payload.indexType",
            "operationType.$": "$.Payload.operationType",
            "embeddingEndpoint.$": "$.Payload.embeddingEndpoint",
          },
        },
        // Original input
        resultPath: "$.TaskResult",
        outputPath: "$.TaskResult.processedPayload",
      },
    );

    const offlineChoice = new sfn.Choice(this, "Offline or Online", {
      comment: "Check if the job is offline or online",
    });

    const offlineGlueJob = new tasks.GlueStartJobRun(this, "OfflineGlueJob", {
      glueJobName: glueJob.jobName,
      integrationPattern: sfn.IntegrationPattern.RUN_JOB,
      arguments: sfn.TaskInput.fromObject({
        "--AOS_ENDPOINT": props.domainEndpoint || "AOS Endpoint Not Created",
        "--BATCH_FILE_NUMBER.$": "$.batchFileNumber",
        "--BATCH_INDICE.$": 'States.Format("{}", $.batchIndices)',
        "--DOC_INDEX_TABLE": props.openSearchIndex,
        "--EMBEDDING_MODEL_ENDPOINT.$": "$.embeddingEndpoint",
        "--ETL_MODEL_ENDPOINT": this.etlEndpoint,
        "--INDEX_TYPE.$": "$.indexType",
        "--JOB_NAME": glueJob.jobName,
        "--OFFLINE": "true",
        "--OPERATION_TYPE.$": "$.operationType",
        "--ProcessedObjectsTable": table.tableName,
        "--QA_ENHANCEMENT.$": "$.qaEnhance",
        "--REGION": props.region,
        "--RES_BUCKET": s3Bucket.bucketName,
        "--S3_BUCKET.$": "$.s3Bucket",
        "--S3_PREFIX.$": "$.s3Prefix",
        "--WORKSPACE_ID.$": "$.workspaceId",
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
        "workspaceId.$": "$.workspaceId",
        "qaEnhance.$": "$.qaEnhance",
        "offline.$": "$.offline",
        "batchFileNumber.$": "$.batchFileNumber",
        // "index" is a special variable within the Map state that represents the current index
        "batchIndices.$": "$$.Map.Item.Index", // Add this if you need to know the index of the current item in the map state
        "indexType.$": "$.indexType",
        "operationType.$": "$.operationType",
        "embeddingEndpoint.$": "$.embeddingEndpoint",
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

    // multiplex the same glue job to offline and online
    const onlineGlueJob = new tasks.GlueStartJobRun(this, "OnlineGlueJob", {
      glueJobName: glueJob.jobName,
      integrationPattern: sfn.IntegrationPattern.RUN_JOB,
      arguments: sfn.TaskInput.fromObject({
        "--AOS_ENDPOINT": props.domainEndpoint,
        "--BATCH_FILE_NUMBER.$": "$.batchFileNumber",
        "--BATCH_INDICE.$": 'States.Format("{}", $.batchIndices)',
        "--DOC_INDEX_TABLE": props.openSearchIndex,
        "--EMBEDDING_MODEL_ENDPOINT.$": "$.embeddingEndpoint",
        "--ETL_MODEL_ENDPOINT": this.etlEndpoint,
        "--INDEX_TYPE.$": "$.indexType",
        "--JOB_NAME": glueJob.jobName,
        "--OFFLINE": "false",
        "--OPERATION_TYPE.$": "$.operationType",
        "--ProcessedObjectsTable": table.tableName,
        "--QA_ENHANCEMENT.$": "$.qaEnhance",
        "--REGION": props.region,
        "--RES_BUCKET": s3Bucket.bucketName,
        "--S3_BUCKET.$": "$.s3Bucket",
        "--S3_PREFIX.$": "$.s3Prefix",
        "--WORKSPACE_ID.$": "$.workspaceId",
        "--job-language": "python",
      }),
    });

    // Notify the result of the glue job
    const notifyTask = new tasks.SnsPublish(this, "NotifyTask", {
      integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
      topic: topic,
      message: sfn.TaskInput.fromText(`Glue job ${glueJob.jobName} completed!`),
    });

    offlineChoice
      .when(sfn.Condition.stringEquals("$.offline", "true"), mapState)
      .when(sfn.Condition.stringEquals("$.offline", "false"), onlineGlueJob);

    // add the notify task to both online and offline branches
    mapState.next(notifyTask);

    const sfnDefinition = lambdaETLIntegration.next(offlineChoice);

    const sfnStateMachine = new sfn.StateMachine(this, "ETLState", {
      definitionBody: sfn.DefinitionBody.fromChainable(sfnDefinition),
      stateMachineType: sfn.StateMachineType.STANDARD,
      // Align with the glue job timeout
      timeout: Duration.minutes(2880),
    });

    // Export the Step function to be used in API Gateway
    this.sfnOutput = sfnStateMachine;
    this.jobName = glueJob.jobName;
    this.jobArn = glueJob.jobArn;
    this.processedObjectsTableName = table.tableName;
    this.workspaceTableName = workspaceTable.tableName;
    this.resBucketName = s3Bucket.bucketName;
  }
}
