import { NestedStack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import * as dotenv from "dotenv";

dotenv.config();

interface llmStackProps extends StackProps {
    _s3ModelAssets: string;
    _crossCodePrefix: string
}

export class LLMStack extends NestedStack {
    _crossEndPointName;

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

        // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
        const inference_image_uri = '763104351884.dkr.ecr.'+ 'us-east-1' +'.amazonaws.com/djl-inference:0.21.0-deepspeed0.8.3-cu117'
        const model = new sagemaker.CfnModel(this, 'cross-model', {
            executionRoleArn: executionRole.roleArn,
            primaryContainer: {
                image: inference_image_uri,
                modelDataUrl: `s3://${props._s3ModelAssets}/${props._crossCodePrefix}/cross_model.tar.gz`,
                environment: {
                    S3_CODE_PREFIX: props._crossCodePrefix,
                },
            },
        });

        // Create endpoint configuration, refer to https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sagemaker.CfnEndpointConfig.html for full options
        const endpointConfig = new sagemaker.CfnEndpointConfig(this, 'cross-endpoint-config', {
            productionVariants: [{
                initialVariantWeight: 1.0,
                modelName: model.attrModelName,
                variantName: 'variantProd',
                containerStartupHealthCheckTimeoutInSeconds: 15*60,
                initialInstanceCount: 1,
                instanceType: 'ml.g4dn.xlarge',
            }],
        });

        // Create endpoint
        const endpoint = new sagemaker.CfnEndpoint(this, 'cross-endpoint', {
            endpointConfigName: endpointConfig.attrEndpointConfigName,
            endpointName: 'cross-endpoint',
        });

        this._crossEndPointName = endpoint.endpointName;
    }
}