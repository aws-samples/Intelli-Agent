import { NestedStack, StackProps, RemovalPolicy, Duration, Aws } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as api from 'aws-cdk-lib/aws-apigateway';
import * as glue from '@aws-cdk/aws-glue-alpha';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3assets from 'aws-cdk-lib/aws-s3-assets';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import path from "path";

interface etlStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _subnets: ec2.ISubnet[];
    _securityGroups: ec2.SecurityGroup;
    _domainEndpoint: string;
    _embeddingEndpoint: string;
    _region: string;
    _subEmail: string;
}

export class EtlStack extends NestedStack {
    _sfnOutput;
    _jobName;
    _jobArn;

    constructor(scope: Construct, id: string, props: etlStackProps) {
        super(scope, id, props);

        const connection = new glue.Connection(this, 'GlueJobConnection', {
            type: glue.ConnectionType.NETWORK,
            subnet: props._subnets[0],
            securityGroups: [props._securityGroups],
          });

        const _S3Bucket = new s3.Bucket(this, 'llm-bot-glue-lib', {
            bucketName: `llm-bot-glue-lib-${Aws.ACCOUNT_ID}-${Aws.REGION}`,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        const extraPythonFiles = new s3deploy.BucketDeployment(this, 'extraPythonFiles', {
            sources: [s3deploy.Source.asset('src/scripts/whl')],
            destinationBucket: _S3Bucket,
            // destinationKeyPrefix: 'llm_bot_dep-0.1.0-py3-none-any.whl',
        });

        // Creata glue job to process files speicified in s3 bucket and prefix
        const glueJob = new glue.Job(this, 'PythonShellJob', {
            executable: glue.JobExecutable.pythonShell({
              glueVersion: glue.GlueVersion.V1_0,
              pythonVersion: glue.PythonVersion.THREE_NINE,
              script: glue.Code.fromAsset(path.join(__dirname, 'scripts/glue-job-script.py')),
              // s3 location of the python script
            //   extraPythonFiles: [glue.Code.fromAsset(path.join(__dirname, 'scripts/llm_bot_dep-0.1.0-py3-none-any.whl'))],
            //   extraPythonFiles: [extraPythonFiles],
            }),
            maxConcurrentRuns:200,
            maxRetries:3,
            connections:[connection],
            maxCapacity:1,
            defaultArguments:{
                '--S3_BUCKET.$': sfn.JsonPath.stringAt('$.s3Bucket'),
                '--S3_PREFIX.$': sfn.JsonPath.stringAt('$.s3Prefix'),
                '--AOS_ENDPOINT': props._domainEndpoint,
                '--REGION': props._region,
                '--EMBEDDING_MODEL_ENDPOINT': props._embeddingEndpoint,
                '--DOC_INDEX_TABLE': 'chatbot-index',
                '--additional-python-modules': 'pdfminer.six==20221105,gremlinpython==3.7.0,langchain==0.0.312,beautifulsoup4==4.12.2,requests-aws4auth==1.2.3,boto3==1.28.69,nougat==0.3.3,openai==0.28.1',
                '--extra-py-files': _S3Bucket.s3UrlForObject('llm_bot_dep-0.1.0-py3-none-any.whl'),
            }
          });

        glueJob.role.addToPrincipalPolicy(
            new iam.PolicyStatement({
                actions: [
                    "sagemaker:InvokeEndpointAsync",
                    "sagemaker:InvokeEndpoint",
                    "s3:*",
                    "es:*",
                ],
                effect: iam.Effect.ALLOW,
                resources: ['*'],
            })
        )

        // Create SNS topic and subscription to notify when glue job is completed
        const topic = new sns.Topic(this, 'etl-topic', {
            displayName: 'etl-topic',
            topicName: 'etl-topic',
        });
        topic.addSubscription(new subscriptions.EmailSubscription(props._subEmail));

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
                '--EMBEDDING_MODEL_ENDPOINT': props._embeddingEndpoint,
                '--REGION': props._region,
                '--OFFLINE': 'true',
            }),
        });

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
                '--EMBEDDING_MODEL_ENDPOINT': props._embeddingEndpoint,
                '--REGION': props._region,
                '--OFFLINE': 'false',
            }),
        });

        // Notify the result of the glue job
        const notifyTask = new tasks.SnsPublish(this, 'NotifyTask', {
            integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
            topic: topic,
            message: sfn.TaskInput.fromText(`Glue job ${glueJob.jobName} completed!`),
        });

        const sfnDefinition = offlineChoice
        .when(sfn.Condition.stringEquals('$.offline', 'true'), offlineGlueJob)
        .when(sfn.Condition.stringEquals('$.offline', 'false'), onlineGlueJob)
        .afterwards().next(notifyTask);
    
        const sfnStateMachine = new sfn.StateMachine(this, 'ETLState', {
            definitionBody: sfn.DefinitionBody.fromChainable(sfnDefinition),
            stateMachineType: sfn.StateMachineType.STANDARD,
            timeout: Duration.minutes(30),
        });

        // Export the Step function to be used in API Gateway
        this._sfnOutput = sfnStateMachine;
        this._jobName = glueJob.jobName;
        this._jobArn = glueJob.jobArn;
    }
}