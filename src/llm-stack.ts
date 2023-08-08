import { NestedStack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import * as dotenv from "dotenv";

dotenv.config();

interface llmStackProps extends StackProps {
    _s3ModelAssets: string;
    _crossCodePrefix: string;
    _embeddingCodePrefix: string;
    _instructCodePrefix: string;
}

export class LLMStack extends NestedStack {
    _crossEndPointName;
    _embeddingEndPointName;
    _instructEndPointName;

    constructor(scope: Construct, id: string, props: llmStackProps) {
        super(scope, id, props);

        // Prepare model asset to download from Hugging Face follow script

        // Specify s3 bucket and prefix for model
        // const _S3Bucket = new s3.Bucket(this, 'llm-rag', {
        //     // Fixed name for serving.properties for now
        //     bucketName: "llm-rag",
        //     blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        // });

        // // Create a Lambda function
        // const fn = new lambda.Function(this, 'justFunction', {
        //     runtime: lambda.Runtime.NODEJS_14_X,
        //     handler: 'index.handler',
        //     code: lambda.Code.fromAsset(path.join(__dirname, 'lambda/custom')),
        //     environment: {
        //         BUCKET_NAME: _S3Bucket.bucketName,
        //     },
        // });

        // // Allow the Lambda function to put objects in the S3 bucket
        // _S3Bucket.grantPut(fn);

        // // Create a custom resource that triggers the Lambda function
        // new cr.AwsCustomResource(this, 'uploadModelAssets', {
        //     onCreate: {
        //     service: 'Lambda',
        //     action: 'invoke',
        //     parameters: {
        //         FunctionName: fn.functionName,
        //     },
        //     physicalResourceId: cr.PhysicalResourceId.of('uploadModelAssets'),
        //     },
        //     policy: cr.AwsCustomResourcePolicy.fromSdkCalls({resources: cr.AwsCustomResourcePolicy.ANY_RESOURCE}),
        // });

        // Create IAM execution role
        const executionRole = new iam.Role(this, 'cross-execution-role', {
            assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess'),
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3FullAccess'),
                iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess'),
            ],
        });

        // CROSS MODEL
        // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
        const crossImageUrl = '763104351884.dkr.ecr.'+ this.region +'.amazonaws.com/djl-inference:0.21.0-deepspeed0.8.3-cu117'
        const crossModel = new sagemaker.CfnModel(this, 'cross-model', {
            executionRoleArn: executionRole.roleArn,
            primaryContainer: {
                image: crossImageUrl,
                modelDataUrl: `s3://${props._s3ModelAssets}/${props._crossCodePrefix}/cross_model.tar.gz`,
                environment: {
                    S3_CODE_PREFIX: props._crossCodePrefix,
                },
            },
        });

        // Create endpoint configuration, refer to https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sagemaker.CfnEndpointConfig.html for full options
        const crossEndpointConfig = new sagemaker.CfnEndpointConfig(this, 'cross-endpoint-config', {
            productionVariants: [{
                initialVariantWeight: 1.0,
                modelName: crossModel.attrModelName,
                variantName: 'variantProd',
                containerStartupHealthCheckTimeoutInSeconds: 15*60,
                initialInstanceCount: 1,
                instanceType: 'ml.g4dn.xlarge',
            }],
        });

        // Create endpoint
        const crossEndpoint = new sagemaker.CfnEndpoint(this, 'cross-endpoint', {
            endpointConfigName: crossEndpointConfig.attrEndpointConfigName,
            endpointName: 'cross-endpoint',
        });

        this._crossEndPointName = crossEndpoint.endpointName;

        // EMBEDDING MODEL
        // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
        const embeddingImageUrl = '763104351884.dkr.ecr.'+ this.region +'.amazonaws.com/djl-inference:0.21.0-deepspeed0.8.3-cu117'
        const embeddingModel = new sagemaker.CfnModel(this, 'embedding-model', {
            executionRoleArn: executionRole.roleArn,
            primaryContainer: {
                image: embeddingImageUrl,
                modelDataUrl: `s3://${props._s3ModelAssets}/${props._embeddingCodePrefix}/s2e_model.tar.gz`,
                environment: {
                    S3_CODE_PREFIX: props._embeddingCodePrefix,
                },
            },
        });

        // Create endpoint configuration, refer to https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sagemaker.CfnEndpointConfig.html for full options
        const embeddingEndpointConfig = new sagemaker.CfnEndpointConfig(this, 'embedding-endpoint-config', {
            productionVariants: [{
                initialVariantWeight: 1.0,
                modelName: embeddingModel.attrModelName,
                variantName: 'variantProd',
                containerStartupHealthCheckTimeoutInSeconds: 15*60,
                initialInstanceCount: 1,
                instanceType: 'ml.g4dn.xlarge',
            }],
        });

        // Create endpoint
        const embeddingEndpoint = new sagemaker.CfnEndpoint(this, 'embedding-endpoint', {
            endpointConfigName: embeddingEndpointConfig.attrEndpointConfigName,
            endpointName: 'embedding-endpoint',
        });

        this._embeddingEndPointName = embeddingEndpoint.endpointName;

        // INSTRUCT MODEL
        // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
        const instructImageUrl = '763104351884.dkr.ecr.'+ this.region +'.amazonaws.com/djl-inference:0.21.0-deepspeed0.8.3-cu117'
        const instructModel = new sagemaker.CfnModel(this, 'instruct-model', {
            executionRoleArn: executionRole.roleArn,
            primaryContainer: {
                image: instructImageUrl,
                modelDataUrl: `s3://${props._s3ModelAssets}/${props._instructCodePrefix}/model.tar.gz`,
                environment: {
                    S3_CODE_PREFIX: props._instructCodePrefix,
                },
            },
        });

        // Create endpoint configuration, refer to https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sagemaker.CfnEndpointConfig.html for full options
        const instructEndpointConfig = new sagemaker.CfnEndpointConfig(this, 'instruct-endpoint-config', {
            productionVariants: [{
                initialVariantWeight: 1.0,
                modelName: instructModel.attrModelName,
                variantName: 'variantProd',
                containerStartupHealthCheckTimeoutInSeconds: 15*60,
                initialInstanceCount: 1,
                instanceType: 'ml.g4dn.xlarge',
            }],
        });

        // Create endpoint
        const instructEndpoint = new sagemaker.CfnEndpoint(this, 'instruct-endpoint', {
            endpointConfigName: instructEndpointConfig.attrEndpointConfigName,
            endpointName: 'instruct-endpoint',
        });

        this._instructEndPointName = instructEndpoint.endpointName;
    }
}