import * as path from 'path';
import { NestedStack, StackProps, CfnOutput, Duration, Size } from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { DockerImageFunction }  from 'aws-cdk-lib/aws-lambda';
import { DockerImageCode, Architecture } from 'aws-cdk-lib/aws-lambda';
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from 'aws-cdk-lib/aws-ec2';

import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { join } from "path";

interface apiStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
}

export class LLMApiStack extends NestedStack {
    // _fnUrl;

    constructor(scope: Construct, id: string, props: apiStackProps) {
        super(scope, id, props);

        // const modelS3Bucket = props._modelS3Bucket;
        // const modelS3Key = props._modelS3Key;

        // const bucket = s3.Bucket.fromBucketName(this, 'llm-model-bucket', modelS3Bucket.toString());

        // const llmApiFn = new lambda.DockerImageFunction(this, 'llm-api', {
        //     code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, 'src')),
        //     environment: {
        //         AWS_LWA_INVOKE_MODE: 'RESPONSE_STREAM',
        //         MODLE_DIR: '/tmp/models',
        //         MODLE_S3_URI: `s3://${modelS3Bucket}/${modelS3Key}`,
        //         DEBUG: 'True',
        //     },
        //     ephemeralStorageSize: Size.gibibytes(5),
        //     memorySize: 10240,
        //     timeout: Duration.minutes(15),
        //     tracing: lambda.Tracing.ACTIVE,
        // });

        // bucket.grantRead(llmApiFn);

        // const alias = llmApiFn.addAlias('live', {
        //     provisionedConcurrentExecutions: 1,
        // });

        // const scalable = alias.addAutoScaling({
        //     maxCapacity: 100,
        //     minCapacity: 1,
        // });
        // scalable.scaleOnUtilization({ utilizationTarget: 0.7 });

        // const fnUrl = alias.addFunctionUrl({
        //     authType: lambda.FunctionUrlAuthType.NONE,
        //     invokeMode: lambda.InvokeMode.RESPONSE_STREAM,
        // });

        // this.fnUrl = fnUrl.url;

        // new CfnOutput(this, 'llm-api-fn-url', { value: fnUrl.url });
        // new CfnOutput(this, 'llm-api-fn-arn', { value: llmApiFn.functionArn });

        const _vpc = props._vpc
        const _securityGroup = props._securityGroup
        const _domainEndpoint = props._domainEndpoint

        const lambdaExecutor = new DockerImageFunction(this,
            "lambda_main_brain", {
            code: DockerImageCode.fromImageAsset(join(__dirname, "../src/lambda/executor")),
            timeout: Duration.minutes(15),
            memorySize: 1024,
            // runtime: 'python3.9',
            // functionName: 'Main_brain',
            vpc: _vpc,
            vpcSubnets: {
                subnets: _vpc.privateSubnets,
            },
            securityGroups: [_securityGroup],
            architecture: Architecture.X86_64,
            environment: {
              aos_endpoint: _domainEndpoint,
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
            }))

    }
}