import { NestedStack, StackProps, RemovalPolicy, Duration, Aws } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as glue from '@aws-cdk/aws-glue-alpha';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import { Function, Runtime, Code, Architecture } from 'aws-cdk-lib/aws-lambda';
import { join } from "path";

// import * as api from 'aws-cdk-lib/aws-apigateway';
// import { off } from 'process';
// import * as s3assets from 'aws-cdk-lib/aws-s3-assets';
// import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';

interface etlStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _subnets: ec2.ISubnet[];
    _securityGroups: ec2.SecurityGroup;
    _domainEndpoint: string;
    _embeddingEndpoint: string[];
    _region: string;
    _subEmail: string;
    _s3ModelAssets: string;
    _OpenSearchIndex: string;
    _imageName: string;
    _etlTag: string;
}

export class EtlStack extends NestedStack {
    _sfnOutput;
    _jobName;
    _jobArn;
    _processedObjectsTable;
    _etlEndpoint: string;
    _resBucketName: string;

    constructor(scope: Construct, id: string, props: etlStackProps) {
        super(scope, id, props);

        const endpointRole = new iam.Role(this, 'etl-endpoint-role', {
            assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess'),
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3FullAccess'),
                iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess'),
            ],
        });
        
        const imageUrlDomain = (this.region === 'cn-north-1' || this.region === 'cn-northwest-1') 
            ? '.amazonaws.com.cn/' 
            : '.amazonaws.com/';

        // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
        const imageUrl = this.account + '.dkr.ecr.' + this.region + imageUrlDomain + props._imageName + ":" + props._etlTag;
        const model = new sagemaker.CfnModel(this, 'etl-model', {
            executionRoleArn: endpointRole.roleArn,
            primaryContainer: {
                image: imageUrl
            },
        });

        // Create endpoint configuration
        const endpointConfig = new sagemaker.CfnEndpointConfig(this, 'etl-endpoint-config', {
            productionVariants: [{
                initialVariantWeight: 1.0,
                modelName: model.attrModelName,
                variantName: 'variantProd',
                containerStartupHealthCheckTimeoutInSeconds: 15*60,
                initialInstanceCount: 1,
                instanceType: 'ml.g4dn.2xlarge',
            }],
        });

        // Create endpoint
        const etlEndpoint = new sagemaker.CfnEndpoint(this, 'etl-endpoint', {
            endpointConfigName: endpointConfig.attrEndpointConfigName,
            endpointName: 'etl-endpoint',
        });
        
        if (typeof etlEndpoint.endpointName === 'undefined') {
            throw new Error('etlEndpoint.endpointName is undefined');
        }

        this._etlEndpoint = etlEndpoint.endpointName;

        const connection = new glue.Connection(this, 'GlueJobConnection', {
            type: glue.ConnectionType.NETWORK,
            subnet: props._subnets[0],
            securityGroups: [props._securityGroups],
        });

        const table = new dynamodb.Table(this, 'ProcessedObjects', {
            partitionKey: { name: 'ObjectKey', type: dynamodb.AttributeType.STRING },
            billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        });

        table.addGlobalSecondaryIndex({
            indexName: 'BucketAndPrefixIndex',
            partitionKey: { name: 'Bucket', type: dynamodb.AttributeType.STRING },
            sortKey: { name: 'Prefix', type: dynamodb.AttributeType.STRING },
        });

        // Add ExpiryTimestamp as an attribute but not as a sort key in the base table
        table.addGlobalSecondaryIndex({
            indexName: 'ExpiryTimestampIndex',
            partitionKey: { name: 'ExpiryTimestamp', type: dynamodb.AttributeType.NUMBER },
            // No sort key for this index
        });

        const _S3Bucket = new s3.Bucket(this, 'llm-bot-glue-res-bucket', {
            // bucketName: `llm-bot-glue-lib-${Aws.ACCOUNT_ID}-${Aws.REGION}`,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        const extraPythonFiles = new s3deploy.BucketDeployment(this, 'extraPythonFiles', {
            sources: [s3deploy.Source.asset(join(__dirname, '../../../lambda/job/dep/dist'))],
            destinationBucket: _S3Bucket,
            // destinationKeyPrefix: 'llm_bot_dep-0.1.0-py3-none-any.whl',
        });

        // Assemble the extra python files list using _S3Bucket.s3UrlForObject('llm_bot_dep-0.1.0-py3-none-any.whl') and _S3Bucket.s3UrlForObject('nougat_ocr-0.1.17-py3-none-any.whl') and convert to string
        const extraPythonFilesList = [_S3Bucket.s3UrlForObject('llm_bot_dep-0.1.0-py3-none-any.whl')].join(',');

        const glueRole = new iam.Role(this, 'ETLGlueJobRole', {
            assumedBy: new iam.ServicePrincipal('glue.amazonaws.com'),
            // The role is used by the glue job to access AOS and by default it has 1 hour session duration which is not enough for the glue job to finish the embedding injection
            maxSessionDuration: Duration.hours(12),
        });
        // TODO: narrow down the policy to specific resources and actions
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
                    // cloudwatch logs
                    "logs:*",
                ],
                effect: iam.Effect.ALLOW,
                resources: ['*'],
            })
        )

        // Creata glue job to process files speicified in s3 bucket and prefix
        const glueJob = new glue.Job(this, 'PythonShellJob', {
            executable: glue.JobExecutable.pythonShell({
                glueVersion: glue.GlueVersion.V3_0,
                pythonVersion: glue.PythonVersion.THREE_NINE,
                script: glue.Code.fromAsset(join(__dirname, '../../../lambda/job/glue-job-script.py')),
            }),
            // Worker Type is not supported for Job Command pythonshell and Both workerType and workerCount must be set...
            // workerType: glue.WorkerType.G_2X,
            // workerCount: 2,
            maxConcurrentRuns: 200,
            maxRetries: 1,
            connections: [connection],
            maxCapacity: 1,
            role: glueRole,
            defaultArguments: {
                '--S3_BUCKET.$': sfn.JsonPath.stringAt('$.s3Bucket'),
                '--S3_PREFIX.$': sfn.JsonPath.stringAt('$.s3Prefix'),
                '--QA_ENHANCEMENT.$': sfn.JsonPath.stringAt('$.qaEnhance'),
                '--AOS_ENDPOINT': props._domainEndpoint,
                '--REGION': props._region,
                '--EMBEDDING_MODEL_ENDPOINT': props._embeddingEndpoint.join(','),
                '--ETL_MODEL_ENDPOINT': this._etlEndpoint,
                '--DOC_INDEX_TABLE': props._OpenSearchIndex,
                '--RES_BUCKET': _S3Bucket.bucketName,
                '--ProcessedObjectsTable': table.tableName,
                '--additional-python-modules': 'langchain==0.0.312,beautifulsoup4==4.12.2,requests-aws4auth==1.2.3,boto3==1.28.84,openai==0.28.1,pyOpenSSL==23.3.0,tenacity==8.2.3,markdownify==0.11.6,mammoth==1.6.0,chardet==5.2.0,python-docx==1.1.0,nltk==3.8.1,pdfminer.six==20221105',
                // '--python-modules-installer-option': '-i https://pypi.tuna.tsinghua.edu.cn/simple',
                // add multiple extra python files
                '--extra-py-files': extraPythonFilesList,
                '--CONTENT_TYPE': 'ug',
                '--EMBEDDING_LANG': 'zh,zh,en,en',
                '--EMBEDDING_TYPE': 'similarity,relevance,similarity,relevance',
                '--AOS_INDEX.$': sfn.JsonPath.stringAt('$.aosIndex'),
            }
        });

        // Create SNS topic and subscription to notify when glue job is completed
        const topic = new sns.Topic(this, 'etl-topic', {
            displayName: 'etl-topic',
            topicName: 'etl-topic',
        });
        topic.addSubscription(new subscriptions.EmailSubscription(props._subEmail));

        // Lambda function to for file deduplication and glue job allocation based on file number
        const lambdaETL = new Function(this,
            "lambdaETL", {
            code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
            handler: "main.lambda_handler",
            runtime: Runtime.PYTHON_3_11,
            timeout: Duration.minutes(15),
            memorySize: 1024,
            architecture: Architecture.X86_64,
        });

        lambdaETL.addToRolePolicy(new iam.PolicyStatement({
            actions: [
                // glue job
                "glue:StartJobRun",
                "s3:List*",
                "s3:Put*",
                "s3:Get*",
            ],
            effect: iam.Effect.ALLOW,
            resources: ['*'],
        }
        ))

        const lambdaETLIntegration = new tasks.LambdaInvoke(this, 'lambdaETLIntegration', {
            lambdaFunction: lambdaETL,
            // Use the result of this invocation to decide how many Glue jobs to run
            resultSelector: {
                "processedPayload": {
                    'batchIndices.$': '$.Payload.batchIndices',
                    's3Bucket.$': '$.Payload.s3Bucket',
                    's3Prefix.$': '$.Payload.s3Prefix',
                    'qaEnhance.$': '$.Payload.qaEnhance',
                    'offline.$': '$.Payload.offline',
                    'aosIndex.$': '$.Payload.aosIndex',
                }
            },
            // we need the original input
            resultPath: '$.TaskResult',
            outputPath: '$.TaskResult.processedPayload',
        });

        const offlineChoice = new sfn.Choice(this, 'Offline or Online', {
            comment: 'Check if the job is offline or online',
        });

        const offlineGlueJob = new tasks.GlueStartJobRun(this, 'OfflineGlueJob', {
            glueJobName: glueJob.jobName,
            integrationPattern: sfn.IntegrationPattern.RUN_JOB,
            arguments: sfn.TaskInput.fromObject({
                '--job-language': 'python',
                '--JOB_NAME': glueJob.jobName,
                '--S3_BUCKET.$': '$.s3Bucket',
                '--S3_PREFIX.$': '$.s3Prefix',
                '--AOS_ENDPOINT': props._domainEndpoint,
                '--EMBEDDING_MODEL_ENDPOINT': props._embeddingEndpoint.join(','),
                '--ETL_MODEL_ENDPOINT': this._etlEndpoint,
                '--DOC_INDEX_TABLE': props._OpenSearchIndex,
                '--REGION': props._region,
                '--RES_BUCKET': _S3Bucket.bucketName,
                '--OFFLINE': 'true',
                '--QA_ENHANCEMENT.$': '$.qaEnhance',
                // Convert the numeric index to a string
                '--BATCH_INDICE.$': 'States.Format(\'{}\', $.batchIndices)',
                '--AOS_INDEX.$': '$.aosIndex',
                '--ProcessedObjectsTable': table.tableName,
                '--CONTENT_TYPE': 'ug',
                '--EMBEDDING_LANG': 'zh,zh,en,en',
                '--EMBEDDING_TYPE': 'similarity,relevance,similarity,relevance',
            }),
        });

        // Define a Map state to run multiple Glue jobs in parallel based on the number of files to process
        const mapState = new sfn.Map(this, 'MapState', {
            // inputPath should point to the root since we want to pass the entire payload to the iterator
            inputPath: '$',
            // itemsPath should reference an array. We need to construct this array based on batchIndices
            itemsPath: sfn.JsonPath.stringAt('$.batchIndices'), 
            // set the max concurrency to 0 to run all the jobs in parallel
            maxConcurrency: 0,
            parameters: {
                // These parameters are passed to each iteration of the map state
                's3Bucket.$': '$.s3Bucket',
                's3Prefix.$': '$.s3Prefix',
                'qaEnhance.$': '$.qaEnhance',
                'aosIndex.$': '$.aosIndex',
                // 'index' is a special variable within the Map state that represents the current index
                'batchIndices.$': '$$.Map.Item.Index' // Add this if you need to know the index of the current item in the map state
            },
            resultPath: '$.mapResults',
        });

        mapState.iterator(offlineGlueJob.addRetry({ errors: ['States.ALL'], interval: Duration.seconds(10), maxAttempts: 3 }));

        // multiplex the same glue job to offline and online
        const onlineGlueJob = new tasks.GlueStartJobRun(this, 'OnlineGlueJob', {
            glueJobName: glueJob.jobName,
            integrationPattern: sfn.IntegrationPattern.RUN_JOB,
            arguments: sfn.TaskInput.fromObject({
                '--job-language': 'python',
                '--JOB_NAME': glueJob.jobName,
                '--S3_BUCKET.$': '$.s3Bucket',
                '--S3_PREFIX.$': '$.s3Prefix',
                '--AOS_ENDPOINT': props._domainEndpoint,
                '--EMBEDDING_MODEL_ENDPOINT': props._embeddingEndpoint.join(','),
                '--ETL_MODEL_ENDPOINT': this._etlEndpoint,
                '--DOC_INDEX_TABLE': props._OpenSearchIndex,
                '--REGION': props._region,
                '--RES_BUCKET': _S3Bucket.bucketName,
                '--OFFLINE': 'false',
                '--QA_ENHANCEMENT.$': '$.qaEnhance',
                // set the batch indice to 0 since we are running online
                '--BATCH_INDICE': '0',
                '--ProcessedObjectsTable': table.tableName,
                '--AOS_INDEX.$': '$.aosIndex',
            }),
        });

        // Notify the result of the glue job
        const notifyTask = new tasks.SnsPublish(this, 'NotifyTask', {
            integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
            topic: topic,
            message: sfn.TaskInput.fromText(`Glue job ${glueJob.jobName} completed!`),
        });

        offlineChoice.when(sfn.Condition.stringEquals('$.offline', 'true'), mapState)
            .when(sfn.Condition.stringEquals('$.offline', 'false'), onlineGlueJob)
        
        // add the notify task to both online and offline branches
        mapState.next(notifyTask);

        const sfnDefinition = lambdaETLIntegration.next(offlineChoice)
    
        const sfnStateMachine = new sfn.StateMachine(this, 'ETLState', {
            definitionBody: sfn.DefinitionBody.fromChainable(sfnDefinition),
            stateMachineType: sfn.StateMachineType.STANDARD,
            // Align with the glue job timeout
            timeout: Duration.minutes(2880),
        });

        // Export the Step function to be used in API Gateway
        this._sfnOutput = sfnStateMachine;
        this._jobName = glueJob.jobName;
        this._jobArn = glueJob.jobArn;
        this._processedObjectsTable = table.tableName
        this._resBucketName = _S3Bucket.bucketName
    }
}