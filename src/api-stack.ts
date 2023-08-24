import { NestedStack, StackProps, Duration, Aws } from 'aws-cdk-lib';
import { DockerImageFunction }  from 'aws-cdk-lib/aws-lambda';
import { DockerImageCode, Architecture } from 'aws-cdk-lib/aws-lambda';
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as s3 from 'aws-cdk-lib/aws-s3';

import { Construct } from 'constructs';
import { join } from "path";

interface apiStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
    _crossEndPoint: string;
    _embeddingEndPoint: string;
    _instructEndPoint: string;
}

export class LLMApiStack extends NestedStack {

    _apiEndpoint;
    constructor(scope: Construct, id: string, props: apiStackProps) {
        super(scope, id, props);

        const _vpc = props._vpc
        const _securityGroup = props._securityGroup
        const _domainEndpoint = props._domainEndpoint

        // s3 bucket for storing documents
        const _S3Bucket = new s3.Bucket(this, 'llm-bot-documents', {
            bucketName: `llm-bot-documents-${Aws.ACCOUNT_ID}-${Aws.REGION}`,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        const lambdaExecutor = new DockerImageFunction(this,
            "lambdaExecutor", {
            code: DockerImageCode.fromImageAsset(join(__dirname, "../src/lambda/executor")),
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
                llm_endpoint: props._crossEndPoint,
                embedding_endpoint: props._embeddingEndPoint,
                cross_endpoint: props._crossEndPoint,
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
            ],
            effect: iam.Effect.ALLOW,
            resources: ['*'],
            }
        ))

        const lambdaEmbedding = new DockerImageFunction(this,
            "lambdaEmbedding", {
            code: DockerImageCode.fromImageAsset(join(__dirname, "../src/lambda/embedding")),
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
                embedding_endpoint: props._embeddingEndPoint,
                cross_endpoint: props._crossEndPoint,
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
        // Define the API Gateway
        const api = new apigw.RestApi(this, 'llmApi', {
            restApiName: 'llmApi',
            description: 'This service serves the LLM API.',
            endpointConfiguration: {
                types: [apigw.EndpointType.REGIONAL]
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

        this._apiEndpoint = api.url
    }
}