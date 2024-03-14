import { NestedStack, StackProps, Duration, Aws } from 'aws-cdk-lib';
import { Function, Runtime, Code, Architecture } from 'aws-cdk-lib/aws-lambda';
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { join } from "path";
import { WebSocketStack } from './websocket-api';
import { ApiQueueStack } from './api-queue';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { LambdaLayers } from '../shared/lambda-layers';
import { BuildConfig } from '../../lib/shared/build-config';

// import { DockerImageFunction, Handler } from 'aws-cdk-lib/aws-lambda';
// import { DockerImageCode } from 'aws-cdk-lib/aws-lambda';

interface apiStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
    _rerankEndPoint: string;
    _embeddingEndPoints: string[];
    _llmModelId: string;
    _instructEndPoint: string;
    _sessionsTableName: string;
    _messagesTableName: string;
    _workspaceTableName: string;
    // type of StepFunctions
    _sfnOutput: sfn.StateMachine;
    _OpenSearchIndex: string;
    _OpenSearchIndexDict: string;
    _jobName: string;
    _jobQueueArn: string;
    _jobDefinitionArn: string;
    _etlEndpoint: string;
    _resBucketName: string;
}

export class LLMApiStack extends NestedStack {

    _apiEndpoint: string = '';
    _documentBucket: string = '';
    _wsEndpoint: string = '';
    constructor(scope: Construct, id: string, props: apiStackProps) {
        super(scope, id, props);

        const _vpc = props._vpc
        const _securityGroup = props._securityGroup
        const _domainEndpoint = props._domainEndpoint
        const _aosIndex = props._OpenSearchIndex
        const _aosIndexDict = props._OpenSearchIndexDict
        const _sessionsTableName = props._sessionsTableName
        const _messagesTableName = props._messagesTableName
        const _workspaceTableName = props._workspaceTableName
        const _jobQueueArn = props._jobQueueArn
        const _jobDefinitionArn = props._jobDefinitionArn
        const _etlEndpoint = props._etlEndpoint
        const _resBucketName = props._resBucketName


        const queueStack = new ApiQueueStack(this, 'LLMQueueStack');
        const sqsStatement = queueStack.sqsStatement;
        const messageQueue = queueStack.messageQueue;

        const lambdaLayers = new LambdaLayers(this);
        const _ApiLambdaExecutorLayer = lambdaLayers.createExecutorLayer();
        const _ApiLambdaEmbeddingLayer = lambdaLayers.createEmbeddingLayer();

        // s3 bucket for storing documents
        const _S3Bucket = new s3.Bucket(this, 'llm-bot-documents', {
            // stack name + bucket name + account id + region
            // bucketName: Aws.STACK_NAME + '-' + Aws.ACCOUNT_ID + '-' + Aws.REGION + '-documents',
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        const lambdaEmbedding = new Function(this,
            "lambdaEmbedding", {
            runtime: Runtime.PYTHON_3_11,
            handler: "main.lambda_handler",
            code: Code.fromAsset(join(__dirname, "../../../lambda/embedding")),
            timeout: Duration.minutes(15),
            memorySize: 4096,
            vpc: _vpc,
            vpcSubnets: {
                subnets: _vpc.privateSubnets,
            },
            securityGroups: [_securityGroup],
            architecture: Architecture.X86_64,
            environment: {
                ETL_MODEL_ENDPOINT: _etlEndpoint,
                REGION: Aws.REGION,
                RES_BUCKET: _resBucketName,
            },
            layers: [_ApiLambdaEmbeddingLayer]
        });

        lambdaEmbedding.addToRolePolicy(new iam.PolicyStatement({
            actions: [
                "sagemaker:InvokeEndpointAsync",
                "sagemaker:InvokeEndpoint",
                "s3:List*",
                "s3:Put*",
                "s3:Get*",
                "es:*",
            ],
            effect: iam.Effect.ALLOW,
            resources: ['*'],
        }
        ))

        const lambdaAos = new Function(this,
            "lambdaAos", {
            runtime: Runtime.PYTHON_3_11,
            handler: "main.lambda_handler",
            code: Code.fromAsset(join(__dirname, "../../../lambda/aos")),
            timeout: Duration.minutes(15),
            memorySize: 1024,
            vpc: _vpc,
            vpcSubnets: {
                subnets: _vpc.privateSubnets,
            },
            securityGroups: [_securityGroup],
            architecture: Architecture.X86_64,
            environment: {
                opensearch_cluster_domain: _domainEndpoint,
                embedding_endpoint: props._embeddingEndPoints[0],
            },
            layers: [_ApiLambdaEmbeddingLayer]
        });

        lambdaAos.addToRolePolicy(new iam.PolicyStatement({
            actions: [
                "sagemaker:InvokeEndpointAsync",
                "sagemaker:InvokeEndpoint",
                "s3:List*",
                "s3:Put*",
                "s3:Get*",
                "es:*",
            ],
            effect: iam.Effect.ALLOW,
            resources: ['*'],
        }
        ))

        const lambdaDdb = new lambda.Function(this, "lambdaDdb", {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: "rating.lambda_handler",
            code: lambda.Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
            environment: {
                SESSIONS_TABLE_NAME: _sessionsTableName,
                MESSAGES_TABLE_NAME: _messagesTableName,
                SESSIONS_BY_USER_ID_INDEX_NAME: "byUserId",
                MESSAGES_BY_SESSION_ID_INDEX_NAME: "bySessionId",
            },
            vpc: _vpc,
            vpcSubnets: {
                subnets: _vpc.privateSubnets,
            },
            securityGroups: [props._securityGroup]
        });

        lambdaDdb.addToRolePolicy(new iam.PolicyStatement({
            actions: [
                "dynamodb:*"
            ],
            effect: iam.Effect.ALLOW,
            resources: ['*'],
        }
        ))

        // Integration with Step Function to trigger ETL process
        // Lambda function to trigger Step Function
        const lambdaStepFunction = new lambda.Function(this, 'lambdaStepFunction', {
            code: lambda.Code.fromAsset(join(__dirname, "../../../lambda/etl")),
            handler: 'sfn_handler.handler',
            runtime: lambda.Runtime.PYTHON_3_11,
            timeout: Duration.seconds(30),
            environment: {
                sfn_arn: props._sfnOutput.stateMachineArn,
            },
            memorySize: 256,
        });

        // grant lambda function to invoke step function
        props._sfnOutput.grantStartExecution(lambdaStepFunction);

        // add s3 event notification when file uploaded to the bucket
        _S3Bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.LambdaDestination(lambdaStepFunction), { prefix: 'documents/' });
        _S3Bucket.grantReadWrite(lambdaStepFunction);

        const lambdaGetETLStatus = new lambda.Function(this, "lambdaGetETLStatus", {
            code: lambda.Code.fromAsset(join(__dirname, "../../../lambda/etl")),
            handler: "get_status.lambda_handler",
            runtime: lambda.Runtime.PYTHON_3_11,
            timeout: Duration.minutes(5),
            environment: {
                sfn_arn: props._sfnOutput.stateMachineArn,
            },
            memorySize: 256,
        });

        lambdaGetETLStatus.addToRolePolicy(new iam.PolicyStatement({
            actions: [
                "states:DescribeExecution",
            ],
            effect: iam.Effect.ALLOW,
            resources: ['*'],
        }));

        const lambdaBatch = new Function(this,
            "lambdaBatch", {
            code: lambda.Code.fromAsset(join(__dirname, "../../../lambda/batch")),
            handler: "main.lambda_handler",
            runtime: lambda.Runtime.PYTHON_3_11,
            timeout: Duration.minutes(15),
            memorySize: 1024,
            vpc: _vpc,
            vpcSubnets: {
                subnets: _vpc.privateSubnets,
            },
            securityGroups: [_securityGroup],
            architecture: Architecture.X86_64,
            environment: {
                document_bucket: _S3Bucket.bucketName,
                opensearch_cluster_domain: _domainEndpoint,
                embedding_endpoint: props._embeddingEndPoints[0],
                jobName: props._jobName,
                jobQueueArn: props._jobQueueArn,
                jobDefinitionArn: props._jobDefinitionArn,
            },
        });

        lambdaBatch.addToRolePolicy(new iam.PolicyStatement({
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
            resources: ['*'],
        }
        ))

        // Define the API Gateway
        const api = new apigw.RestApi(this, 'llmApi', {
            restApiName: 'llmApi',
            description: 'This service serves the LLM API.',
            endpointConfiguration: {
                types: [apigw.EndpointType.REGIONAL]
            },
            defaultCorsPreflightOptions: {
                allowHeaders: [
                    'Content-Type',
                    'X-Amz-Date',
                    'Authorization',
                    'X-Api-Key',
                    'X-Amz-Security-Token'
                ],
                allowMethods: apigw.Cors.ALL_METHODS,
                allowCredentials: true,
                allowOrigins: apigw.Cors.ALL_ORIGINS,
            },
            deployOptions: {
                stageName: 'v1',
                metricsEnabled: true,
                loggingLevel: apigw.MethodLoggingLevel.INFO,
                dataTraceEnabled: true,
                tracingEnabled: true,
            },
        });

        // Define the API Gateway Lambda Integration with proxy and no integration responses
        const lambdaEmbeddingIntegration = new apigw.LambdaIntegration(lambdaEmbedding, { proxy: true, });

        // Define the API Gateway Method
        const apiResourceEmbedding = api.root.addResource('extract');
        apiResourceEmbedding.addMethod('POST', lambdaEmbeddingIntegration);

        // Define the API Gateway Lambda Integration with proxy and no integration responses
        const lambdaAosIntegration = new apigw.LambdaIntegration(lambdaAos, { proxy: true, });

        // All AOS wrapper should be within such lambda
        const apiResourceAos = api.root.addResource('aos');
        apiResourceAos.addMethod('POST', lambdaAosIntegration);

        // Add Get method to query & search index in OpenSearch, such embedding lambda will be updated for online process
        apiResourceAos.addMethod('GET', lambdaAosIntegration);

        // Define the API Gateway Lambda Integration with proxy and no integration responses
        const lambdaDdbIntegration = new apigw.LambdaIntegration(lambdaDdb, { proxy: true, });

        // All AOS wrapper should be within such lambda
        const apiResourceDdb = api.root.addResource('feedback');
        apiResourceDdb.addMethod('POST', lambdaDdbIntegration);

        const apiResourceStepFunction = api.root.addResource('etl');
        apiResourceStepFunction.addMethod('POST', new apigw.LambdaIntegration(lambdaStepFunction));

        const apiResourceETLStatus = apiResourceStepFunction.addResource("status")
        apiResourceETLStatus.addMethod('GET', new apigw.LambdaIntegration(lambdaGetETLStatus));

        // Define the API Gateway Lambda Integration to invoke Batch job
        const lambdaBatchIntegration = new apigw.LambdaIntegration(lambdaBatch, { proxy: true, });

        // Define the API Gateway Method
        const apiResourceBatch = api.root.addResource('batch');
        apiResourceBatch.addMethod('POST', lambdaBatchIntegration);

        if (BuildConfig.DEPLOYMENT_MODE === 'ALL') {
            const lambdaExecutor = new Function(this,
                "lambdaExecutor", {
                runtime: Runtime.PYTHON_3_11,
                handler: "main.lambda_handler",
                code: Code.fromAsset(join(__dirname, "../../../lambda/executor")),
                timeout: Duration.minutes(15),
                memorySize: 1024,
                vpc: _vpc,
                vpcSubnets: {
                    subnets: _vpc.privateSubnets,
                },
                securityGroups: [_securityGroup],
                architecture: Architecture.X86_64,
                environment: {
                    aos_endpoint: _domainEndpoint,
                    llm_model_endpoint_name: props._instructEndPoint,
                    llm_model_id: props._llmModelId,
                    embedding_endpoint: props._embeddingEndPoints[0],
                    zh_embedding_endpoint: props._embeddingEndPoints[0],
                    en_embedding_endpoint: props._embeddingEndPoints[1],
                    rerank_endpoint: props._rerankEndPoint,
                    aos_index: _aosIndex,
                    aos_index_dict: _aosIndexDict,
                    sessions_table_name: _sessionsTableName,
                    messages_table_name: _messagesTableName,
                    workspace_table: _workspaceTableName,
                },
                layers: [_ApiLambdaExecutorLayer]
            });

            lambdaExecutor.addToRolePolicy(new iam.PolicyStatement({
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
                resources: ['*'],
            }
            ))
            lambdaExecutor.addToRolePolicy(sqsStatement);
            lambdaExecutor.addEventSource(new lambdaEventSources.SqsEventSource(messageQueue));

            // Define the API Gateway Lambda Integration with proxy and no integration responses
            const lambdaExecutorIntegration = new apigw.LambdaIntegration(lambdaExecutor, { proxy: true, });

            // Define the API Gateway Method
            const apiResourceLLM = api.root.addResource('llm');
            apiResourceLLM.addMethod('POST', lambdaExecutorIntegration);

            const lambdaDispatcher = new Function(this,
                "lambdaDispatcher", {
                runtime: Runtime.PYTHON_3_11,
                handler: "main.lambda_handler",
                code: Code.fromAsset(join(__dirname, "../../../lambda/dispatcher")),
                timeout: Duration.minutes(15),
                memorySize: 1024,
                vpc: _vpc,
                vpcSubnets: {
                    subnets: _vpc.privateSubnets,
                },
                securityGroups: [_securityGroup],
                architecture: Architecture.X86_64,
                environment: {
                    SQS_QUEUE_URL: messageQueue.queueUrl,
                }
            });
            lambdaDispatcher.addToRolePolicy(sqsStatement);

            const webSocketApi = new WebSocketStack(this, 'WebSocketApi', {
                dispatcherLambda: lambdaDispatcher,
                sendMessageLambda: lambdaExecutor,
            });

            this._wsEndpoint = webSocketApi.websocketApiStage.api.apiEndpoint;
        }


        this._apiEndpoint = api.url
        this._documentBucket = _S3Bucket.bucketName
    }
}