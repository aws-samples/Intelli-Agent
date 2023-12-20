import { NestedStack, StackProps, Duration, Aws } from 'aws-cdk-lib';
import { DockerImageFunction, Handler }  from 'aws-cdk-lib/aws-lambda';
import { DockerImageCode, Architecture } from 'aws-cdk-lib/aws-lambda';
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { join } from "path";
import { WebSocketApi } from '@aws-cdk/aws-apigatewayv2-alpha';
import { WebSocketStack } from './websocket-api';

interface apiStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
    _rerankEndPoint: string;
    _embeddingEndPoints: string[];
    _instructEndPoint: string;
    _chatSessionTable: string;
    // type of StepFunctions
    _sfnOutput: sfn.StateMachine;
    _OpenSearchIndex: string;
    _OpenSearchIndexDict: string;
}

export class LLMApiStack extends NestedStack {

    _apiEndpoint;
    _documentBucket;
    constructor(scope: Construct, id: string, props: apiStackProps) {
        super(scope, id, props);

        const _vpc = props._vpc
        const _securityGroup = props._securityGroup
        const _domainEndpoint = props._domainEndpoint
        const _aosIndex = props._OpenSearchIndex
        const _aosIndexDict = props._OpenSearchIndexDict
        const _chatSessionTable = props._chatSessionTable

        // s3 bucket for storing documents
        const _S3Bucket = new s3.Bucket(this, 'llm-bot-documents', {
            // stack name + bucket name + account id + region
            // bucketName: Aws.STACK_NAME + '-' + Aws.ACCOUNT_ID + '-' + Aws.REGION + '-documents',
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        const lambdaExecutor = new DockerImageFunction(this,
            "lambdaExecutor", {
            code: DockerImageCode.fromImageAsset(join(__dirname, "../../../lambda/executor")),
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
                llm_endpoint: props._instructEndPoint,
                embedding_endpoint: props._embeddingEndPoints[0],
                zh_embedding_endpoint: props._embeddingEndPoints[0],
                en_embedding_endpoint: props._embeddingEndPoints[1],
                rerank_endpoint: props._rerankEndPoint,
                aos_index: _aosIndex,
                aos_index_dict: _aosIndexDict,
                chat_session_table: _chatSessionTable,
            },
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

        const lambdaEmbedding = new DockerImageFunction(this,
            "lambdaEmbedding", {
            code: DockerImageCode.fromImageAsset(join(__dirname, "../../../lambda/embedding")),
            timeout: Duration.minutes(15),
            memorySize: 4096,
            vpc: _vpc,
            vpcSubnets: {
                subnets: _vpc.privateSubnets,
            },
            securityGroups: [_securityGroup],
            architecture: Architecture.X86_64,
            environment: {
                document_bucket: _S3Bucket.bucketName,
                opensearch_cluster_domain: _domainEndpoint,
                llm_endpoint: props._instructEndPoint,
                embedding_endpoint: props._embeddingEndPoints[0],
                cross_endpoint: props._rerankEndPoint,
            },
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

        const lambdaAos = new DockerImageFunction(this,
            "lambdaAos", {
            code: DockerImageCode.fromImageAsset(join(__dirname, "../../../lambda/aos")),
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
        const lambdaExecutorIntegration = new apigw.LambdaIntegration(lambdaExecutor, { proxy: true, });

        // Define the API Gateway Method
        const apiResourceLLM = api.root.addResource('llm');
        apiResourceLLM.addMethod('POST', lambdaExecutorIntegration);

        // Define the API Gateway Lambda Integration with proxy and no integration responses
        const lambdaEmbeddingIntegration = new apigw.LambdaIntegration(lambdaEmbedding, { proxy: true, });

        // Define the API Gateway Method
        const apiResourceEmbedding = api.root.addResource('embedding');
        apiResourceEmbedding.addMethod('POST', lambdaEmbeddingIntegration);

        // Add Get method to query & search index in OpenSearch, such embedding lambda will be updated for online process
        apiResourceEmbedding.addMethod('GET', lambdaEmbeddingIntegration);

        // Define the API Gateway Lambda Integration with proxy and no integration responses
        const lambdaAosIntegration = new apigw.LambdaIntegration(lambdaAos, { proxy: true, });

        // All AOS wrapper should be within such lambda
        const apiResourceAos = api.root.addResource('aos');
        apiResourceAos.addMethod('POST', lambdaAosIntegration);

        // Add Get method to query & search index in OpenSearch, such embedding lambda will be updated for online process
        apiResourceAos.addMethod('GET', lambdaAosIntegration);

        // Integration with Step Function to trigger ETL process
        // Lambda function to trigger Step Function
        const lambdaStepFunction = new lambda.Function(this, 'lambdaStepFunction', {
            // format to avoid indent error, using inline for simplicity no more container pack time needed
            code: lambda.Code.fromInline
            (`
import json
import boto3
import os
client = boto3.client('stepfunctions')
def handler(event, context):
    # First check the event for possible S3 created event
    inputPayload = {}
    if 'Records' in event:
        print('S3 created event detected')
        # TODO, Aggregate the bucket and key from the event object for S3 created event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        # Pass the bucket and key to the Step Function, align with the input schema in etl-stack.ts
        inputPayload=json.dumps({'s3Bucket': bucket, 's3Prefix': key, 'offline': 'false', 'qaEnhance': 'false'})
    else:
        print('API Gateway event detected')
        # Parse the body from the event object
        body = json.loads(event['body'])
        # Pass the parsed body to the Step Function
        inputPayload=json.dumps(body)

    response = client.start_execution(
        stateMachineArn=os.environ['sfn_arn'],
        input=inputPayload
    )
    return {
        'statusCode': 200,
        'body': json.dumps('Step Function triggered, Step Function ARN: ' + response['executionArn'] + ' Input Payload: ' + inputPayload)
    }
            `),
            handler: 'index.handler',
            runtime: lambda.Runtime.PYTHON_3_9,
            timeout: Duration.seconds(30),
            environment: {
                sfn_arn: props._sfnOutput.stateMachineArn,
            },
            memorySize: 256,
        });

        // grant lambda function to invoke step function
        props._sfnOutput.grantStartExecution(lambdaStepFunction);

        const apiResourceStepFunction = api.root.addResource('etl');
        apiResourceStepFunction.addMethod('POST', new apigw.LambdaIntegration(lambdaStepFunction));

        // add s3 event notification when file uploaded to the bucket
        _S3Bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.LambdaDestination(lambdaStepFunction), { prefix: 'documents/' });
        _S3Bucket.grantReadWrite(lambdaStepFunction);

        const webSocketApi = new WebSocketStack(this, 'WebSocketApi', {
            sendMessageLambda: lambdaExecutor,
        });

        this._apiEndpoint = api.url
        this._documentBucket = _S3Bucket.bucketName
    }
}